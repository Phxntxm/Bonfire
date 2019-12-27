import asyncio
import asyncpg

from collections import defaultdict

from . import config


class Cache:
    """A class to hold the entires that are called on every message/command"""

    def __init__(self, db):
        self.db = db
        self.prefixes = {}
        self.ignored = defaultdict(dict)
        self.custom_permissions = defaultdict(dict)
        self.restrictions = defaultdict(dict)

    async def setup(self):
        # Make sure db is setup first
        await self.db.setup()

        await self.load_prefixes()
        await self.load_custom_permissions()
        await self.load_restrictions()
        await self.load_ignored()

    async def load_ignored(self):
        query = """
SELECT
    id, ignored_channels, ignored_members
FROM
    guilds
WHERE
    array_length(ignored_channels, 1) > 0 OR
    array_length(ignored_members, 1) > 0
"""
        rows = await self.db.fetch(query)
        for row in rows:
            self.ignored[row['id']]['members'] = row['ignored_members']
            self.ignored[row['id']]['channels'] = row['ignored_channels']

    async def load_prefixes(self):
        query = """
SELECT
    id, prefix
FROM
    guilds
WHERE
    prefix IS NOT NULL
"""
        rows = await self.db.fetch(query)
        for row in rows:
            self.prefixes[row['id']] = row['prefix']

    def update_prefix(self, guild, prefix):
        self.prefixes[guild.id] = prefix

    async def load_custom_permissions(self):
        query = """
SELECT
    guild, command, permission
FROM
    custom_permissions
WHERE
    permission IS NOT NULL
"""
        rows = await self.db.fetch(query)
        for row in rows:
            self.custom_permissions[row['guild']][row['command']] = row['permission']

    def update_custom_permission(self, guild, command, permission):
        self.custom_permissions[guild.id][command.qualified_name] = permission

    async def load_restrictions(self):
        query = """
SELECT
    guild, source, from_to, destination
FROM
    restrictions
"""
        rows = await self.db.fetch(query)
        for row in rows:
            opt = {"source": row['source'], "destination": row['destination']}
            from_restrictions = self.restrictions[row['guild']].get(row['from_to'], [])
            from_restrictions.append(opt)
            self.restrictions[row['guild']][row['from_to']] = from_restrictions

    def add_restriction(self, guild, from_to, restriction):
        restrictions = self.restrictions[guild.id].get(from_to, [])
        restrictions.append(restriction)
        self.restrictions[guild.id][from_to] = restrictions

    def remove_restriction(self, guild, from_to, restriction):
        restrictions = self.restrictions[guild.id].get(from_to, [])
        if restriction in restrictions:
            restrictions.remove(restriction)
            self.restrictions[guild.id][from_to] = restrictions


class DB:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.opts = config.db_opts
        self.cache = {}
        self._pool = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(**self.opts)

    async def setup(self):
        await self.connect()

    async def _query(self, call, query, *args, **kwargs):
        """this will acquire a connection and make the call, then return the result"""
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                return await getattr(connection, call)(query, *args, **kwargs)

    async def execute(self, *args, **kwargs):
        return await self._query("execute", *args, **kwargs)

    async def fetch(self, *args, **kwargs):
        return await self._query("fetch", *args, **kwargs)

    async def fetchrow(self, *args, **kwargs):
        return await self._query("fetchrow", *args, **kwargs)

    async def fetchval(self, *args, **kwargs):
        return await self._query("fetchval", *args, **kwargs)

    async def upsert(self, table, data):
        keys = values = ""
        for num, k in enumerate(data.keys()):
            if num > 0:
                keys += ", "
                values += ", "
            keys += k
            values += f"${num}"
        query = f"INSERT INTO {table} ({keys}) VALUES ({values}) ON CONFLICT DO UPDATE"
        return await self.execute(query, *data.values())
