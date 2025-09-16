from fastapi_admin.models import AbstractAdmin
from tortoise.models import Model
from tortoise import fields

class Admin(AbstractAdmin):
    username = fields.CharField(max_length=20)
    
class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50)
    email = fields.CharField(max_length=100)
    role = fields.CharField(max_length=20)
    is_verified = fields.BooleanField(default=False)
    
    class Meta:
        table = "users"