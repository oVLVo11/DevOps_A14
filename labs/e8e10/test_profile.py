import json, tempfile, unittest
from pathlib import Path
from lab import fixture,scan,patch,commit

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_independent_known_edges(self):
        r=scan(self.p)
        self.assertEqual(r['actual']['main.o'],['config.h','main.c'])
        self.assertEqual({(f['type'],f['dependency']) for f in r['findings']},{('MISSING','config.h'),('REDUNDANT','unused.h')})

    def test_unchanged_reuses_both_targets(self):
        r=scan(self.p,scan(self.p));self.assertEqual(r['reused'],['main.o','helper.o']);self.assertEqual(r['refreshed'],[])

    def test_include_added_invalidates_cache(self):
        old=scan(self.p)
        (self.p/'main.c').write_text('#include "extra.h"\n'+(self.p/'main.c').read_text());commit(self.p,'new include')
        r=scan(self.p,old)
        self.assertIn(['MISSING','main.o','extra.h'],r['added']);self.assertEqual(len(r['refreshed']),2)

    def test_indirect_header_include_invalidates_history(self):
        old=scan(self.p)
        (self.p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
        commit(self.p,'indirect header include')
        result=scan(self.p,old)
        self.assertEqual(result['actual']['main.o'],['config.h','extra.h','main.c'])
        self.assertIn(['MISSING','main.o','extra.h'],result['added'])
        self.assertEqual(result['reused'],[])
        self.assertEqual(result['refreshed'],['main.o','helper.o'])

    def test_declaration_change_reuses_actual_graph_and_resolves_md(self):
        old=scan(self.p)
        makefile=self.p/'Makefile'
        makefile.write_text(makefile.read_text().replace('main.c unused.h','main.c unused.h config.h'))
        commit(self.p,'declare config header')
        result=scan(self.p,old)
        self.assertEqual(result['actual'],old['actual'])
        self.assertEqual(result['reused'],['main.o','helper.o'])
        self.assertIn(['MISSING','main.o','config.h'],result['resolved'])
        self.assertEqual([(x['type'],x['dependency']) for x in result['findings']],[('REDUNDANT','unused.h')])

    def test_header_configuration_change_refreshes_without_new_edge(self):
        old=scan(self.p)
        (self.p/'config.h').write_text('#define VALUE 2\n')
        commit(self.p,'header value change')
        for _ in range(5):
            incremental=scan(self.p,old)
            full=scan(self.p)
            self.assertEqual(incremental['actual'],full['actual'])
            self.assertEqual(incremental['declared'],full['declared'])
            self.assertEqual(incremental['findings'],full['findings'])
            self.assertEqual(incremental['refreshed'],['main.o','helper.o'])

    def test_patch_preserves_redundant_dependency(self):
        r=scan(self.p);diff,plan=patch(self.p,r)
        self.assertIn('+main.o: main.c unused.h config.h',diff)
        self.assertNotIn('-\tgcc',diff)
        self.assertNotIn('config.h',(self.p/'Makefile').read_text())

    def test_old_report_rejected(self):
        r=scan(self.p);r['commit']='0'*40
        with self.assertRaisesRegex(ValueError,'STALE_REPORT'):patch(self.p,r)

    def test_unsafe_dependency_rejected(self):
        r=scan(self.p);r['findings']=[{'type':'MISSING','target':'main.o','dependency':'../outside.h'}]
        with self.assertRaisesRegex(ValueError,'UNSAFE_PATH'):patch(self.p,r)

    def test_unsupported_configuration_rejected(self):
        (self.p/'Makefile').write_text((self.p/'Makefile').read_text().replace('-O0','-include unknown.h'))
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_FLAGS'):scan(self.p)

if __name__=='__main__':unittest.main()
