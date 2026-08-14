from fastapi import FastAPI,Depends, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional, List

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

app=FastAPI()

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
def get_session():
    with Session(engine) as session:
        yield session

class TaskCreate(SQLModel):
    title:str = Field(min_length=1)
    description:str
    completed:bool=False
    created_at:str
class Task(TaskCreate,table=True):
    id:Optional[int] =Field(default=None,primary_key=True)
    

@app.get("/")
async def read_root():
    return {"message : api is running"}   
@app.post("/tasks",response_model=Task)
async def create_task(task:TaskCreate,session:Session=Depends(get_session)):
    db_task = Task.model_validate(task)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task 
@app.get("/tasks",response_model=List[Task])
async def get_tasks(session:Session=Depends(get_session)):
    tasks = session.exec(select(Task)).all()
    return tasks
@app.get("/tasks/{task_id}",response_model=Task)
async def get_task(task_id:int,session:Session=Depends(get_session)):
    task = session.get(Task, task_id)
    if not task :
        raise HTTPException(status_code=404,detail="task pas trouve")
    return task

@app.put("/tasks/{task_id}")
async def update_task(task_id:int,task:TaskCreate,session:Session=Depends(get_session)):
    old_task=session.get(Task,task_id)
    if not old_task:
        raise HTTPException(status_code=404,detail="task pas trouve")
    old_task.title=task.title
    old_task.description=task.description
    old_task.created_at=task.created_at
    old_task.completed=task.completed
    session.add(old_task)
    session.commit()
    session.refresh(old_task)
    return old_task

@app.delete("/tasks/{task_id}")
async def delete_task(task_id:int,session:Session=Depends(get_session)):
    task=session.get(Task,task_id)
    if not task:
        raise HTTPException(status_code=404,detail="task pas trouve")
    session.delete(task)
    session.commit()
    return {"message":"task deleted"}
