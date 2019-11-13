# zenchi

zenchi is a python3 application that communicates with AniDB UDP API. It provides an interface to convert raw responses strings into python objects. It does very little by itself and its only intention is to parse data for other applications to use.

Currently, only Data commands are supported.

## Installing

```pip install -U zenchi```


## Usage

Fairly straightforward:

```python
>>> import zenchi
>>> zenchi.create_socket(anidb_server='api.anidb.net', anidb_port=9000)
<socket.socket ...>
>>> zenchi.ping(nat=1)
({'port': 25065}, 300)
```

Every command response is a tuple (data, code). data is a dictionary of variable keys containing the parsed response, and code is the response code.

### Environment variables

`ZENCHI_CLIENTNAME` and `ZENCHI_CLIENTVERSION` should be replaced by your own keys generated at AniDB site. (no guarantee these values are valid at the time of your reading!)

```
ZENCHI_CLIENTNAME=devel
ZENCHI_CLIENTVERSION=1

ANIDB_SERVER=api.anidb.net
ANIDB_PORT=9000

ANIDB_USERNAME=xXGodKillerXx
ANIDB_PASSWORD=hunter2
```

If these values are set, the socket is created automatically and it's much simpler. You can skip the call for `create_socket` entirely and just call the commands:

```python
>>> import zenchi
>>> zenchi.auth()
({'session': 'ELahj'}, 200)
>>> zenchi.character(1)
(..., 235)
```

### Anime masks

The `ANIME` command receives a mask as parameter to filter the anime data. zenchi provides an easy way to create these masks with the module `zenchi.mappings.anime.mask`.

```python
>>> import zenchi.mappings.anime.mask as amask
>>> zenchi.anime(amask.aid | amask.romaji_name | amask.english_name | amask.short_name | amask.year, aid=3433)
({'aid': 3433, 'english_name': 'Mushi-Shi', 'romaji_name': 'Mushishi', 'short_name': ['Mushi'], 'updated_at': datetime.datetime(2019, 11, 10, 19, 55, 18, 1000), 'year': '2005-2006'}, 230)
```


## Cache

zenchi uses a very basic optional MongoDB database as cache, named `anidb_cache`. It uses the environment variable `MONGODB_URI` to check the connection string. If the variable is not set, a warning will be issued and all cache usage will be ignored (highly unadvised, as per AniDB specifications).

Any operations that use the cache have the parameter `use_cache` that defaults to `True`. You can set this to `False` to skip the cache for that specific command (for example, when you want to update the cached data). All cached data also returns a `updated_at` key (see example above), which is the last time that data was updated in the database.

If you don't want to use `anidb_cache` or `MONGODB_URI`, manually call `zenchi.cache.setup` with the appropriate values before sending requests to the API.


## Features

It's actually fairly simple to add new commands to zenchi, and I just wrote what I personally intend to use.
Feel free to send PRs or request something in the issues.

## License

This project is under MIT License.

For data collection and usage, make sure to read [AniDB Policies](https://anidb.net/policy)
