from sqlalchemy import Column, String,ForeignKey,Integer
from sqlalchemy.dialects.mysql import  TINYINT
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Skills(Base):
    __tablename__ = 'Skills'

    skillId = Column(String, primary_key=True)
    skillName = Column(String)
    skillValue = Column(String,unique=True)

class MercorUsers(Base):
    __tablename__ = 'MercorUsers'

    userId = Column(String, primary_key=True)
    email = Column(String,unique=True)
    name = Column(String)
    fullTimeSalary = Column(String)
    partTimeSalary = Column(String)
    phone = Column(String)
    fullTime = Column(TINYINT)
    partTime = Column(TINYINT)
    workAvailability=Column(String)
    preferredRole=Column(String)
    partTimeSalaryCurrency=Column(String)
    fullTimeSalaryCurrency=Column(String)
    fullTimeAvailability=Column(Integer)
    partTimeAvailability=Column(Integer)


class MercorUserSkills(Base):
    __tablename__ = 'MercorUserSkills'

    userId = Column(String, ForeignKey('MercorUsers.userId'),primary_key=True)
    skillId = Column(String, ForeignKey('Skills.skillId'),primary_key=True)

class UserResume(Base):
    __tablename__ = 'UserResume'

    resumeId = Column(String,primary_key=True)
    userId = Column(String, ForeignKey('MercorUsers.userId'),unique=True)

class PersonalInformation(Base):
    __tablename__ = 'PersonalInformation'

    personalInformationId = Column(String,primary_key=True)
    location = Column(String)
    resumeId = Column(String, ForeignKey('UserResume.resumeId'))

class WorkExperience(Base):
    __tablename__ = 'WorkExperience'

    workExperienceId = Column(String,primary_key=True)    
    company = Column(String)                    
    role= Column(String)
    startDate= Column(String)
    endDate= Column(String)
    description= Column(String)
    locationCity= Column(String)
    locationCountry= Column(String)
    resumeId = Column(String, ForeignKey('UserResume.resumeId'))


class Education(Base):
    __tablename__ = 'Education'

    educationId = Column(String,primary_key=True)
    resumeId = Column(String, ForeignKey('UserResume.resumeId'))
    degree=Column(String)
    major=Column(String)
    school=Column(String)
    startDate=Column(String)
    endDate=Column(String)
    grade=Column(String)
    resumeId=Column(String)

