import pandas as pd
from ETC.Data_Base_Model import User, InputData, GeneData, OverallAverageGeneData, AgeGroupAverageGeneData
from datetime import datetime
import logging
import json
from sqlalchemy import func

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_fixed_data(file_path="fixed_data.json"):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            fixed_data_json = json.load(f)
        return pd.DataFrame(fixed_data_json)
    except FileNotFoundError:
        logger.info(f"No fixed_data.json found at {file_path}. Using default values.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading fixed data: {e}")
        raise

def process_data(data):
    data['생년월일'] = pd.to_datetime(data['생년월일'], errors='coerce')
    data['날짜'] = pd.to_datetime(data['날짜'], errors='coerce')
    data['Age'] = data['생년월일'].apply(lambda x: calculate_age(x) if pd.notna(x) else 0)
    data['AgeGroup'] = data['Age'].apply(lambda x: (x // 10) * 10)
    return data

def calculate_age(birthdate):
    today = datetime.now()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def record_exists(session, name, birthdate, date):
    return session.query(User).filter_by(name=name, birthdate=birthdate, date=date).first() is not None

def save_user_and_input_data(data, session):
    user_ids = []
    for _, row in data.iterrows():
        if record_exists(session, row['이름'], row['생년월일'], row['날짜']):
            logger.info(f"Skipping duplicate entry for {row['이름']} on {row['날짜']}")
            continue

        user = User(
            name=row['이름'],
            birthdate=row['생년월일'],
            date=row['날짜'],
            age_group=row['AgeGroup']
        )
        session.add(user)
        session.flush()

        user_ids.append(user.id)

        session.add(InputData(
            user_id=user.id,
            b_actin=row['b-actin'],
            TIMP3=row['TIMP3'],
            COL10A1=row['COL10A1'],
            FLG=row['FLG'],
            AQP3=row['AQP3']
        ))

        session.add(GeneData(
            user_id=user.id,
            TIMP3=row['TIMP3'] - row['b-actin'],
            COL10A1=(80 - row['COL10A1']) - row['b-actin'],
            FLG=(80 - row['FLG']) - row['b-actin'],
            AQP3=row['AQP3'] - row['b-actin']
        ))
    session.commit()
    return user_ids

def update_overall_averages(session):
    overall_avg = session.query(
        func.avg(GeneData.TIMP3).label('TIMP3'),
        func.avg(GeneData.COL10A1).label('COL10A1'),
        func.avg(GeneData.FLG).label('FLG'),
        func.avg(GeneData.AQP3).label('AQP3')
    ).first()

    if overall_avg:
        overall_data = session.query(OverallAverageGeneData).first() or OverallAverageGeneData()
        overall_data.TIMP3 = overall_avg.TIMP3 or 0
        overall_data.COL10A1 = overall_avg.COL10A1 or 0
        overall_data.FLG = overall_avg.FLG or 0
        overall_data.AQP3 = overall_avg.AQP3 or 0
        session.add(overall_data)
        session.commit()

def update_age_group_averages(session):
    age_group_avgs = session.query(
        User.age_group,
        func.avg(GeneData.TIMP3).label('TIMP3'),
        func.avg(GeneData.COL10A1).label('COL10A1'),
        func.avg(GeneData.FLG).label('FLG'),
        func.avg(GeneData.AQP3).label('AQP3')
    ).join(GeneData, User.id == GeneData.user_id)\
     .group_by(User.age_group).all()

    for row in age_group_avgs:
        age_group_data = session.query(AgeGroupAverageGeneData).filter_by(age_group=row.age_group).first() \
                         or AgeGroupAverageGeneData(age_group=row.age_group)
        age_group_data.TIMP3 = row.TIMP3 or 0
        age_group_data.COL10A1 = row.COL10A1 or 0
        age_group_data.FLG = row.FLG or 0
        age_group_data.AQP3 = row.AQP3 or 0
        session.add(age_group_data)
    session.commit()

def initialize_fixed_data(session):
    if not session.query(OverallAverageGeneData).first():
        fixed_data = load_fixed_data()
        if not fixed_data.empty:
            fixed_data_processed = process_data(fixed_data)
            save_user_and_input_data(fixed_data_processed, session)
        else:
            overall_data = OverallAverageGeneData(TIMP3=50.0, COL10A1=50.0, FLG=50.0, AQP3=50.0)
            session.add(overall_data)
            session.commit()
        update_overall_averages(session)
        update_age_group_averages(session)
        logger.info("Fixed data initialized.")

def save_to_db(input_data, session):
    df = process_data(input_data)
    user_ids = save_user_and_input_data(df, session)
    if user_ids:
        update_overall_averages(session)
        update_age_group_averages(session)
    return user_ids