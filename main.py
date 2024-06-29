from collections import defaultdict
import json
from fastapi import APIRouter, FastAPI,Depends
from sqlalchemy import and_, case, column,func
from sqlalchemy.future import select
from constants import RedisKeys
from db_models import Skills,MercorUserSkills,MercorUsers,UserResume,Education,PersonalInformation,WorkExperience
from helpers import find_budget, find_skills,find_employment_types
from models import ChatRequest
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
app = FastAPI()
origins = [
    "https://chabot-sigma.vercel.app"
    "http://localhost",
    "http://localhost:3000",
]

# Add CORSMiddleware to the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)
router = APIRouter(prefix="/api/v1")

@router.get("/")
def root():
    return {"message": "Hello World Live"}

@router.get("/ping")
def root():
    return {"message": "pong"}

@router.post("/chat")
async def chat(request: ChatRequest,db: AsyncSession = Depends(get_db)):
    skills=r.get(RedisKeys.SKILLS.value) 
    if not skills :
        skills = (await db.execute(select(Skills))).scalars().all()
        r.set(RedisKeys.SKILLS.value,json.dumps([{"skillId":skill.skillId,"skillName":skill.skillName,"skillValue":skill.skillValue} for skill in skills]))
    else :
        skills=json.loads(skills)
    skill_names = {skill["skillValue"].lower():skill["skillId"] for skill in skills}
    context = request.context.model_dump()
    #parse skills
    parsed_skills = find_skills(skill_names,request.prompt)

    if len(parsed_skills) != 0 : 
        context["skills"] =  context["skills"] | parsed_skills

    if len(context["skills"])==0:
        return {"bot_msg": "Please provide the skills that you are searching for along with the budget in USD, or wether you are searching for a part-time or full-time employee."}

    #parse employement type
    parsed_employment_types=find_employment_types(request.prompt)
    #parse budget
    parsed_budget=find_budget(request.prompt)

    if len(parsed_employment_types) !=0 :
        context["employment_type"]=parsed_employment_types
    if len(parsed_budget) !=0 :
        #only supports number budgets as of now TO DO : use nlp to support more cases
        # maximum numeric_data
        maxi=max([int(element) for element in parsed_budget if int(element)],default=0)

        #parsing numbers for budget, should not take small numbers which might represent age etc
        if maxi>=50 :
            context["budget"]=maxi

    context["skills"]=list(context["skills"])
    #check if context is in cache
    cache_response = r.get(f"context:{context}") 
    if cache_response :
        return json.loads(cache_response)

    #scalar search and get all the skills of every user satisfying the scalar filters and rank user according to count of most number of matched skills in the context
    context_skill_ids = [skill_names.get(skill,"") for skill in context["skills"]]
    res = list(await db.execute(select(MercorUsers.userId,MercorUsers.name,MercorUsers.email,MercorUsers.phone,MercorUsers.workAvailability,
                                MercorUsers.fullTime,MercorUsers.fullTimeSalary,MercorUsers.fullTimeAvailability,MercorUsers.partTime,MercorUsers.partTimeSalary,
                                MercorUsers.partTimeAvailability, 
                                func.sum(case({skill_id: 1 for skill_id in context_skill_ids},value=MercorUserSkills.skillId,else_=0)).label("count"))
                        .join(MercorUserSkills,MercorUserSkills.userId==MercorUsers.userId)
                        .filter(and_(MercorUserSkills.skillId.in_(context_skill_ids),and_(MercorUsers.partTime==1,
                        MercorUsers.partTimeSalary<=int(context["budget"])) if "part" in context["employment_type"] else MercorUsers.partTime==0,
                        and_(MercorUsers.fullTime==1,MercorUsers.fullTimeSalary<=int(context["budget"])) if "full" in context["employment_type"] else MercorUsers.fullTime==0))
                        .group_by(MercorUserSkills.userId,MercorUsers.name,MercorUsers.email,MercorUsers.phone,MercorUsers.workAvailability,
                                MercorUsers.fullTime,MercorUsers.fullTimeSalary,MercorUsers.fullTimeAvailability,MercorUsers.partTime,MercorUsers.partTimeSalary,
                                MercorUsers.partTimeAvailability).order_by(column("count").desc()).limit(3)))
    users=defaultdict(dict)
    context_user_ids =[user_id for user_id,*_ in res]
    filtered_context_user_ids=[]
    #check if user skills are in cache 
    for user_id in context_user_ids :
        cached_user_skills = r.get(f"skills:{user_id}")
        if cached_user_skills :
            users[user_id]["skills"]=json.loads(cached_user_skills)
        else :
            filtered_context_user_ids.append(user_id)
            
    skill_ids= {skill["skillId"]:skill["skillName"] for skill in skills}

    #get all the skill ids of the users not in the cache and in the context 
    context_user_skills = await db.execute(select(MercorUserSkills.userId,func.group_concat(MercorUserSkills.skillId.op('separator')(';'))).filter(MercorUserSkills.userId.in_(filtered_context_user_ids)).group_by(MercorUserSkills.userId))
   
    for user_id,user_skill_ids in context_user_skills :
        user_skills = [skill_ids[skill_id] for skill_id in user_skill_ids.split(";")]
        r.set(f"skills:{user_id}",json.dumps(user_skills))
        users[user_id]["skills"]=user_skills

    for user_id,name,email,phone,workAvailability,fullTime,fullTimeSalary,fullTimeAvailability,partTime,partTimeSalary,partTimeAvailability,count in res :
        users[user_id].update({
            "name":name,
            "phone":phone,
            "email":email,
            "workAvailability":workAvailability,
            "fullTime":fullTime,
            "fullTimeSalary":fullTimeSalary,
            "partTime":partTime,
            "partTimeSalary":partTimeSalary,
            "fullTimeAvailability":fullTimeAvailability,
            "partTimeAvailability":partTimeAvailability,
            "skills_in_context":int(count),
            "workExperience":[],
            "education":[],
            "location":""
        })

    res = await db.execute((select(UserResume.userId,PersonalInformation.location,
        func.group_concat(
            func.concat(WorkExperience.role,"::",WorkExperience.company,"::",WorkExperience.locationCity,"::",WorkExperience.locationCountry,"::",WorkExperience.startDate,"::",WorkExperience.endDate,"::").distinct().op('separator')(';')
        ).label('experience'),
        func.group_concat(
            func.concat(Education.degree,"::",Education.major,"::",Education.grade,"::",Education.school,"::",Education.startDate,"::",Education.endDate).distinct().op('separator')(';')
        ).label('education')
    )).join(PersonalInformation,PersonalInformation.resumeId==UserResume.resumeId)
    .join(WorkExperience,WorkExperience.resumeId==UserResume.resumeId)
    .join(Education,Education.resumeId==UserResume.resumeId)
    .filter((UserResume.userId.in_(users.keys()))
            )
    .group_by(UserResume.userId,PersonalInformation.location)
            )
    
    #parse work-ex and education 
    for user_id,location,work,education in res :
        for val in work.split(";") :
            temp=val.split("::")
            if len(temp) >=6 :
                users[user_id]["workExperience"].append({
                    "role":temp[0],
                    "company":temp[1],
                    "locationCity":temp[2],
                    "locationCountry":temp[3],
                    "startDate":temp[4],
                    "endDate":temp[5],
                    "description":"",
                })
        for val in education.split(";") :
            temp=val.split("::")
            if len(temp) >=6 :
                users[user_id]["education"].append({
                    "degree":temp[0],
                    "major":temp[1],
                    "grade":temp[2],
                    "school":temp[3],
                    "endDate":temp[4],
                    "startDate":temp[5],
                })
        users[user_id]["location"]=location

    bot_msg=f'I was able to find candidates who meet your requirements. Would you like to refine the search with additional criteria {"" if len(parsed_employment_types) != 0 else ", such as availability (part-time or full-time)"} {"" if len(parsed_budget) != 0 else ", the compensation being offered per month in USD"} ?'
    response = {"bot_msg":bot_msg,"context":context,"candidates":list(users.values())}
    if len(users) !=0 :
        r.set(f"context:{context}",json.dumps(response),ex=60*60*60)
    return response

app.include_router(router)
