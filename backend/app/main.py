import re
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt
from jwt import InvalidTokenError
from .config import settings
from .database import Base, engine, get_db
from .models import Article, User, Workspace, WorkspaceMember
from .schemas import ArticleIn, ArticleOut, ArticleUpdate, LoginIn, RegisterIn, TokenOut, UserOut, WorkspaceCreate, WorkspaceOut
from .security import create_access_token, hash_password, verify_password

app = FastAPI(title='DevOps Knowledge Hub API', version='1.0.0')
origins = [origin.strip() for origin in settings.cors_origins.split(',') if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
security = HTTPBearer(auto_error=False)

@app.on_event('startup')
def startup():
    # For a small local starter. Use Alembic migrations before production deployments.
    Base.metadata.create_all(bind=engine)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail='Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload['sub'])
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail='Invalid or expired access token')
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail='User no longer exists')
    return user

def membership(db: Session, workspace_id: int, user_id: int) -> WorkspaceMember:
    member = db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id))
    if not member:
        raise HTTPException(status_code=404, detail='Workspace not found')
    return member

def can_edit(db: Session, workspace_id: int, user_id: int) -> WorkspaceMember:
    member = membership(db, workspace_id, user_id)
    if member.role not in ('owner', 'editor'):
        raise HTTPException(status_code=403, detail='Editor or owner role required')
    return member

def slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug[:240] or 'article'

def article_out(article: Article) -> ArticleOut:
    return ArticleOut.model_validate(article)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/api/v1/auth/register', response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail='Email is already registered')
    user = User(email=email, display_name=data.display_name.strip(), password_hash=hash_password(data.password))
    db.add(user); db.flush()
    slug_base = slugify(data.display_name)
    workspace = Workspace(name=f"{data.display_name}'s workspace", slug=f'{slug_base}-{user.id}', description='Personal DevOps knowledge workspace', owner_id=user.id)
    db.add(workspace); db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role='owner'))
    db.commit()
    return TokenOut(access_token=create_access_token(user.id))

@app.post('/api/v1/auth/login', response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Email or password is incorrect')
    return TokenOut(access_token=create_access_token(user.id))

@app.get('/api/v1/auth/me', response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

@app.get('/api/v1/workspaces', response_model=list[WorkspaceOut])
def list_workspaces(user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Workspace).join(WorkspaceMember).where(WorkspaceMember.user_id == user.id).order_by(Workspace.created_at.desc())
    return list(db.scalars(stmt).all())

@app.post('/api/v1/workspaces', response_model=WorkspaceOut, status_code=201)
def create_workspace(data: WorkspaceCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    slug = f'{slugify(data.name)}-{user.id}-{uuid4().hex[:6]}'
    workspace = Workspace(name=data.name.strip(), slug=slug, description=data.description.strip(), owner_id=user.id)
    db.add(workspace); db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role='owner'))
    db.commit(); db.refresh(workspace)
    return workspace

@app.post('/api/v1/workspaces/{workspace_id}/members', status_code=201)
def add_workspace_member(workspace_id: int, data: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    caller = membership(db, workspace_id, user.id)
    if caller.role != 'owner':
        raise HTTPException(status_code=403, detail='Only workspace owners can manage members')
    email = str(data.get('email', '')).strip().lower()
    role = str(data.get('role', 'viewer')).strip().lower()
    if role not in ('editor', 'viewer'):
        raise HTTPException(status_code=422, detail='Role must be editor or viewer')
    target = db.scalar(select(User).where(User.email == email))
    if not target:
        raise HTTPException(status_code=404, detail='User must register before being added to a workspace')
    existing = db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == target.id))
    if existing:
        existing.role = role
        db.commit()
        return {'user_id': target.id, 'email': target.email, 'role': role, 'updated': True}
    db.add(WorkspaceMember(workspace_id=workspace_id, user_id=target.id, role=role))
    db.commit()
    return {'user_id': target.id, 'email': target.email, 'role': role, 'updated': False}

@app.get('/api/v1/workspaces/{workspace_id}/members')
def list_workspace_members(workspace_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership(db, workspace_id, user.id)
    stmt = select(WorkspaceMember, User).join(User, User.id == WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
    return [{'user_id': member.user_id, 'email': target.email, 'display_name': target.display_name, 'role': member.role} for member, target in db.execute(stmt).all()]

@app.get('/api/v1/workspaces/{workspace_id}/articles', response_model=list[ArticleOut])
def list_workspace_articles(workspace_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership(db, workspace_id, user.id)
    stmt = select(Article).where(Article.workspace_id == workspace_id).order_by(Article.updated_at.desc())
    return [article_out(a) for a in db.scalars(stmt).all()]

@app.post('/api/v1/workspaces/{workspace_id}/articles', response_model=ArticleOut, status_code=201)
def create_article(workspace_id: int, data: ArticleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    can_edit(db, workspace_id, user.id)
    published = data.status == 'published'
    article = Article(workspace_id=workspace_id, author_id=user.id, title=data.title.strip(), slug=slugify(data.title), summary=data.summary.strip(), body=data.body, context=data.context, tags=','.join(t.strip() for t in data.tags if t.strip()), status=data.status, is_public=data.is_public and published, published_at=datetime.now(timezone.utc) if published else None)
    db.add(article); db.commit(); db.refresh(article)
    return article_out(article)

@app.get('/api/v1/articles/public', response_model=list[ArticleOut])
def list_public_articles(context: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Article).where(Article.status == 'published', Article.is_public.is_(True)).order_by(Article.published_at.desc())
    if context:
        stmt = stmt.where(Article.context == context)
    return [article_out(a) for a in db.scalars(stmt).all()]

@app.get('/api/v1/articles/{article_id}', response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    # Public detail endpoint only; private drafts are available via the authenticated workspace endpoint.
    article = db.get(Article, article_id)
    if not article or article.status != 'published' or not article.is_public:
        raise HTTPException(status_code=404, detail='Article not found')
    return article_out(article)

@app.patch('/api/v1/articles/{article_id}', response_model=ArticleOut)
def update_article(article_id: int, data: ArticleUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail='Article not found')
    can_edit(db, article.workspace_id, user.id)
    changes = data.model_dump(exclude_unset=True)
    if 'title' in changes and changes['title'] is not None:
        article.title = changes['title'].strip(); article.slug = slugify(article.title)
    if 'tags' in changes and changes['tags'] is not None:
        changes['tags'] = ','.join(t.strip() for t in changes['tags'] if t.strip())
    for key, value in changes.items():
        if key not in ('title', 'tags') and value is not None:
            setattr(article, key, value)
    if article.status == 'published' and article.published_at is None:
        article.published_at = datetime.now(timezone.utc)
    if article.status != 'published':
        article.published_at = None; article.is_public = False
    db.commit(); db.refresh(article)
    return article_out(article)

@app.delete('/api/v1/articles/{article_id}', status_code=204)
def delete_article(article_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail='Article not found')
    can_edit(db, article.workspace_id, user.id)
    db.delete(article); db.commit()
