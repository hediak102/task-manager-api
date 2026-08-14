from fastapi import FastAPI
from pydantic import BaseModel

app=FastAPI()

class Task(BaseModel):
    id:int
    title:str
    description:str
    completed:bool
    created_at:str

@app.get("/")
async def read_root():
    return {"message : api is running"}   
fake_db_task=[ {"id": 1, "title": "doing the dishes", "description": "i need to do the dishes", "completed": False, "created_at": "12:30"},
    {"id": 2, "title": "doing the clothes", "description": "i need to wash the clothes", "completed": False, "created_at": "14:30"}]

@app.post("/tasks")
async def create_task(task:Task):
    fake_db_task.append(task.dict())
    return {"task created ok ."}
@app.get("/tasks")
async def get_tasks():
    return fake_db_task
@app.get("/tasks/{task_id}")
async def get_task(task_id:int):
    for i in fake_db_task:
        if (task_id==i['id']):
            return{"voici le task": f"avec id {task_id}", " task" : i}
    return {"task pas trouvee"}
@app.put("/tasks/{task_id}")
async def update_task(task_id:int,task:Task):
    for index, t in enumerate(fake_db_task):
        if t["id"] == task_id:
            fake_db_task[index] = task.dict()
            return {"message": "task updated"}
    return {"task pas trouvee"}
@app.delete("/tasks/{task_id}")
async def delete_task(task_id:int):
    for i in fake_db_task:
        if task_id==i['id']:
            fake_db_task.remove(i)
            return{"task deleted"}
    return {"task pas trouvee"}
