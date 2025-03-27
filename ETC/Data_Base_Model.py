from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    birthdate = db.Column(db.Date, nullable=False)
    date = db.Column(db.Date, nullable=False)
    age_group = db.Column(db.Integer, nullable=False)

class InputData(db.Model):
    __tablename__ = 'input_data'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    b_actin = db.Column(db.Float, nullable=False)
    TIMP3 = db.Column(db.Float, nullable=False)
    COL10A1 = db.Column(db.Float, nullable=False)
    FLG = db.Column(db.Float, nullable=False)
    AQP3 = db.Column(db.Float, nullable=False)

class GeneData(db.Model):
    __tablename__ = 'gene_data'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    TIMP3 = db.Column(db.Float, nullable=False)
    COL10A1 = db.Column(db.Float, nullable=False)
    FLG = db.Column(db.Float, nullable=False)
    AQP3 = db.Column(db.Float, nullable=False)

class OverallAverageGeneData(db.Model):
    __tablename__ = 'overall_average_gene_data'
    id = db.Column(db.Integer, primary_key=True)
    TIMP3 = db.Column(db.Float, nullable=False)
    COL10A1 = db.Column(db.Float, nullable=False)
    FLG = db.Column(db.Float, nullable=False)
    AQP3 = db.Column(db.Float, nullable=False)

class AgeGroupAverageGeneData(db.Model):
    __tablename__ = 'age_group_average_gene_data'
    id = db.Column(db.Integer, primary_key=True)
    age_group = db.Column(db.Integer, nullable=False)
    TIMP3 = db.Column(db.Float, nullable=False)
    COL10A1 = db.Column(db.Float, nullable=False)
    FLG = db.Column(db.Float, nullable=False)
    AQP3 = db.Column(db.Float, nullable=False)