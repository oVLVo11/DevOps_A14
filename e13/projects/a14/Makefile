CC = gcc
CFLAGS = -O0

app: main.o helper.o
	$(CC) main.o helper.o -o app

main.o: main.c config.h
	$(CC) $(CFLAGS) -c main.c -o main.o

helper.o: helper.c
	$(CC) $(CFLAGS) -c helper.c -o helper.o

.PHONY: test clean
test: app
	./app | diff - expected.txt

clean:
	rm -f app main.o helper.o
