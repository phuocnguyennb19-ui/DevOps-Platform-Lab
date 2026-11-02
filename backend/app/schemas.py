from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RegisterIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    display_name: str

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default='', max_length=2000)

class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    owner_id: int

class ArticleIn(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    summary: str = Field(default='', max_length=5000)
    body: str = Field(default='', max_length=200000)
    context: str = Field(default='DevOps', max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=30)
    status: str = Field(default='draft', pattern='^(draft|published)$')
    is_public: bool = False

class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=220)
    summary: str | None = Field(default=None, max_length=5000)
    body: str | None = Field(default=None, max_length=200000)
    context: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = Field(default=None, max_length=30)
    status: str | None = Field(default=None, pattern='^(draft|published)$')
    is_public: bool | None = None

class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workspace_id: int
    author_id: int
    title: str
    slug: str
    summary: str
    body: str
    context: str
    tags: str
    status: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
