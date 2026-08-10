CC ?= gcc
CFLAGS = -Wall -Wextra -O2

TARGET = can_fota_flasher
SRCS = can_fota_flasher.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS)

clean:
	rm -f $(TARGET)
