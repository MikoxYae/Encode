from motor.motor_asyncio import AsyncIOMotorClient
import config

class Database:
    def __init__(self, uri, db_name):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.users = self.db.users

    async def add_user(self, user_id, first_name):
        user = await self.users.find_one({"id": user_id})
        if not user:
            await self.users.insert_one({"id": user_id, "first_name": first_name})

    async def get_user(self, user_id):
        return await self.users.find_one({"id": user_id})

    async def get_all_users(self):
        return self.users.find({})

# initialize DB instance
db = Database(config.DB_URI, config.DB_NAME)
