from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os

# ==========================================
# 1. 数据库配置 (Database Configuration)
# ==========================================
# 在 DevSecOps 实践中，这里通常通过 os.getenv() 获取，避免硬编码
# 这是一个非常适合测试 Gitleaks 的地方：你可以故意在这里硬编码一个密码，看扫描器能否发现
# 目前为了演示方便，使用 SQLite
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")

# check_same_thread=False 仅用于 SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ==========================================
# 2. 数据库模型 (ORM Models)
# ==========================================
class Message(Base):
    """
    消息数据表
    在 SAST 扫描中，我们要确保对这里的查询没有 SQL 注入风险
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # 匿名用户名，实际项目中可能需要脱敏处理
    username = Column(String, index=True, default="Anonymous") 
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 预留字段：IP地址 (用于后续演示日志审计和隐私合规扫描)
    ip_address = Column(String, nullable=True)

# 创建所有表
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. Pydantic 验证模型 (Schemas)
# ==========================================
class MessageCreate(BaseModel):
    """
    接收消息的请求体
    """
    content: str = Field(..., min_length=1, max_length=1000, description="消息内容")
    username: str = Field("Anonymous", max_length=50, description="显示的用户名")

class MessageResponse(BaseModel):
    """
    返回消息的响应体
    """
    id: int
    username: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

# ==========================================
# 4. 依赖项 (Dependencies)
# ==========================================
def get_db():
    """
    获取数据库会话，请求结束后自动关闭
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 5. FastAPI 应用初始化
# ==========================================
app = FastAPI(
    title="Anonymous Chat API",
    description="一个用于 DevSecOps 演练的匿名聊天室后端",
    version="1.0.0"
)

# 配置 CORS (允许前端跨域访问)
# 在安全审计中，这里如果设为 allow_origins=["*"] 可能会被标记为低危风险
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 6. API 路由 (Routes)
# ==========================================

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Anonymous Chat API is running"}

@app.post("/messages/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    """
    发送一条新消息
    """
    # 这是一个潜在的业务逻辑检测点：是否过滤了敏感词？
    db_message = Message(
        username=message.username, 
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

@app.get("/messages/", response_model=list[MessageResponse])
def get_messages(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取消息列表 (默认返回最近的100条)
    """
    messages = db.query(Message).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
    return messages

# ==========================================
# 7. 故意留下的漏洞 (用于 DevSecOps 演练)
# ==========================================
# 下面的代码包含明显的 SQL 注入风险，仅用于测试 SAST 工具 (如 Semgrep/SonarQube)
# 千万不要在生产环境使用！

@app.get("/unsafe_search/")
def unsafe_search_messages(query: str, db: Session = Depends(get_db)):
    """
    [VULNERABLE] 这是一个故意留下的 SQL 注入漏洞接口
    用于测试你的 SAST 流水线是否能拦截
    """
    from sqlalchemy import text
    # 直接拼接字符串，极其危险！
    sql = f"SELECT * FROM messages WHERE content LIKE '%{query}%'"
    result = db.execute(text(sql)).fetchall()
    return {"result": [row._asdict() for row in result]}

@app.post("/unsafe_messages/", status_code=status.HTTP_201_CREATED)
def unsafe_add_message(message: MessageCreate, db: Session = Depends(get_db)):
    """
    [VULNERABLE] 这是一个故意留下的 SQL 注入漏洞接口 (INSERT)
    用于测试你的 SAST/DAST 流水线是否能拦截
    """
    from sqlalchemy import text
    # 直接拼接字符串，极其危险！
    sql = f"INSERT INTO messages (username, content, created_at) VALUES ('{message.username}', '{message.content}', '{datetime.utcnow()}')"
    db.execute(text(sql))
    db.commit()
    return {"status": "message added (unsafe)", "content": message.content}
