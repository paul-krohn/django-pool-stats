## Intent ##

This software was designed with the rules and practices of the San Francisco Pool Association in mind. If it happens to work with your league, go for it. It is doesn't a pull request with the changes needed to abstract away the differences would be appreciated.

## Installation ##

Development has been done exclusively on a Mac, the instructions are [here](Mac_Install.md). There is nothing in this software that requires OS X, or even a Unix-like OS; if you use or develop it on another OS, a pull request adding those instructions or accommodations would be most welcome.

### Environment Variables ###

You can set the database and memcached connection information as environment variables; for example:
```
export DJANGO_DB_PASS="some_password"
```

All are optional/depend on your configuration:
* `DJANGO_DB_PASS`
* `DJANGO_DB_NAME`
* `DJANGO_DB_USER`
* `DJANGO_DB_HOST`
* `DJANGO_MEMCACHED`

## Contributing ##
Pull requests are welcome! Follow the standard Github workflow:
* fork
* create a branch
* add your feature or fix and related tests
* create a pull request

Before you embark on substantial work, you might want to open an issue, which will allow for some dialog on preferred approaches before you get too far down a path that is not mutually agreeable.
