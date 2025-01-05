# Auto Signal Trader

## Beschrijving

## Installatie
1. Copy the json config example file
```bash
cp config.example.json config.json

## Use of Telegram
This program uses the official Telegram API and hence is part of the Telegram ecosystem.

## Use MT5 op linux
https://github.com/lucas-campagna/mt5linux

## suppress wine fixme messages

How to Suppress or Handle These Messages
Suppressing Output: If you find these messages annoying and want to suppress them, you can adjust the Wine debug settings. You can do this by setting the WINEDEBUG environment variable. For example, you can run your application with the following command to suppress "fixme" messages:

```bash
WINEDEBUG=-fixme wine your_application.exe

This command tells Wine to ignore all "fixme" messages.

Redirecting Output: If you want to keep the messages but redirect them to a file instead of displaying them in the terminal, you can do so like this:
bash
```bash
wine your_application.exe &> wine_output.log

This will redirect both standard output and standard error to wine_output.log.