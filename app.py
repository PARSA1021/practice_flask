from flask import Flask, render_template, request, jsonify, redirect, url_for, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import os
import pandas as pd
import logging
from datetime import datetime
from typing import Union
from ETC.Data_Base_Model import db, User, InputData, GeneData, OverallAverageGeneData, AgeGroupAverageGeneData
from process_data import save_to_db, initialize_fixed_data
from visualization import plot_radar_chart, plot_bar_chart

# Flask 애플리케이션 설정
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 캐시 설정
cache = Cache(config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache'})
cache.init_app(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHARTS_FOLDER = os.path.join("static", "Charts", "user_charts")

# Blueprint 생성
main_bp = Blueprint('main', __name__)

# 유틸리티 함수들
def get_comparison_symbol(value: float, avg: float) -> str:
    """값이 평균 이상이면 '+'를, 미만이면 '-'를 반환합니다."""
    return "+" if value >= avg else "-"

def safe_format(value: Union[float, None]) -> str:
    """숫자를 소수점 둘째 자리로 포맷팅하거나, None이면 '-'를 반환합니다."""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"

# Route 함수들
@main_bp.route('/')
def index():
    """홈 페이지"""
    return render_template('index.html', today=datetime.now().strftime('%Y-%m-%d'))

@main_bp.route('/save', methods=['POST'])
def save_data():
    """데이터 저장 및 보고서 URL 반환"""
    data = request.json
    required_fields = ["name", "birth_date", "test_date", "b_actin", "TIMP3", "COL10A1", "FLG", "AQP3"]

    # 필수 항목 체크
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        logger.warning(f"Missing fields: {missing_fields}")
        return jsonify({"error": f"다음 필수 항목을 입력해주세요: {', '.join(missing_fields)}"}), 400

    # 데이터 처리 및 저장
    try:
        input_df = pd.DataFrame([{
            "이름": data['name'],
            "생년월일": data['birth_date'],
            "날짜": data['test_date'],
            "b-actin": float(data['b_actin']),
            "TIMP3": float(data['TIMP3']),
            "COL10A1": float(data['COL10A1']),
            "FLG": float(data['FLG']),
            "AQP3": float(data['AQP3'])
        }])
    except ValueError as ve:
        logger.error(f"Invalid data format: {ve}")
        return jsonify({"error": "숫자 필드에 올바른 값을 입력해주세요."}), 400

    # DB에 데이터 저장 및 보고서 URL 반환
    with db.session() as session:
        try:
            user_ids = save_to_db(input_df, session)
            if not user_ids:
                return jsonify({"error": "이미 존재하는 데이터입니다. 중복 확인 후 다시 시도해주세요."}), 400

            user = session.query(User).filter_by(id=user_ids[0]).first()
            gene_data = session.query(GeneData).filter_by(user_id=user_ids[0]).first()
            overall_avg = session.query(OverallAverageGeneData).first()
            age_avg = session.query(AgeGroupAverageGeneData).filter_by(age_group=user.age_group).first()

            if not all([user, gene_data, overall_avg, age_avg]):
                logger.error(f"Missing data for user {user_ids[0]}")
                return jsonify({"error": "데이터 처리 중 오류가 발생했습니다."}), 500

            name = input_df['이름'].iloc[0]
            test_date = input_df['날짜'].iloc[0].strftime('%Y-%m-%d')

            # 차트 생성
            radar_chart = plot_radar_chart(gene_data, overall_avg, age_avg, name, test_date)
            bar_chart = plot_bar_chart(gene_data, overall_avg, age_avg, name, test_date)

            session.commit()
            return jsonify({"report_url": url_for('main.serve_report', name=name, date=test_date.replace('-', ''))}), 200
        except Exception as e:
            session.rollback()
            logger.error(f"Error in save_data: {e}", exc_info=True)
            return jsonify({"error": "서버 오류가 발생했습니다. 다시 시도해주세요."}), 500

@main_bp.route('/report/<name>/<date>')
@cache.cached(timeout=300)
def serve_report(name, date):
    """보고서 페이지 표시"""
    with db.session() as session:
        try:
            # 데이터 조회
            user = session.query(User).filter_by(name=name, date=f"{date[:4]}-{date[4:6]}-{date[6:]}").first()
            if not user:
                return render_template('error.html', message="사용자를 찾을 수 없습니다."), 404

            gene_data = session.query(GeneData).filter_by(user_id=user.id).first()
            overall_avg = session.query(OverallAverageGeneData).first()
            age_avg = session.query(AgeGroupAverageGeneData).filter_by(age_group=user.age_group).first()
            input_data = session.query(InputData).filter_by(user_id=user.id).first()

            if not all([gene_data, overall_avg, age_avg, input_data]):
                logger.error(f"Missing data for {name}/{date}")
                return render_template('error.html', message="데이터가 누락되었습니다."), 500

            # 차트 및 테이블 생성
            test_date = user.date.strftime('%Y-%m-%d')
            radar_chart = plot_radar_chart(gene_data, overall_avg, age_avg, name, test_date, check_exists=True)
            bar_chart = plot_bar_chart(gene_data, overall_avg, age_avg, name, test_date, check_exists=True)

            gene_data_table = generate_gene_data_table(gene_data, overall_avg, age_avg)

            # 보고서 데이터
            report_data = {
                "name": name,
                "birth_date": user.birthdate.strftime('%Y-%m-%d'),
                "test_date": test_date,
                "gene_data": generate_gene_data_list(input_data, gene_data),
                "gene_data_table": gene_data_table,
                "radar_chart": radar_chart,
                "bar_chart": bar_chart
            }
            return render_template('report.html', **report_data)
        except Exception as e:
            logger.error(f"Error serving report: {e}", exc_info=True)
            return render_template('error.html', message="보고서 생성 중 오류가 발생했습니다."), 500

def generate_gene_data_list(input_data, gene_data):
    """유전자 데이터 리스트 생성"""
    return [
        {"category": "대조군", "value": input_data.b_actin},
        {"category": "미백", "value": gene_data.TIMP3},
        {"category": "주름", "value": gene_data.COL10A1},
        {"category": "탄력", "value": gene_data.FLG},
        {"category": "수분", "value": gene_data.AQP3}
    ]

def generate_gene_data_table(gene_data, overall_avg, age_avg):
    """유전자 데이터 테이블 생성"""
    return [
        ["유전자", "발현량", "전체 평균 비교", "평가", "연령대 평균 비교", "평가"],
        ["미백", 
         safe_format(gene_data.TIMP3),
         get_comparison_symbol(gene_data.TIMP3, overall_avg.TIMP3),
         "양호" if gene_data.TIMP3 >= overall_avg.TIMP3 else "개선 필요",
         get_comparison_symbol(gene_data.TIMP3, age_avg.TIMP3),
         "양호" if gene_data.TIMP3 >= age_avg.TIMP3 else "개선 필요"],
        ["주름", 
         safe_format(gene_data.COL10A1),
         get_comparison_symbol(gene_data.COL10A1, overall_avg.COL10A1),
         "양호" if gene_data.COL10A1 >= overall_avg.COL10A1 else "개선 필요",
         get_comparison_symbol(gene_data.COL10A1, age_avg.COL10A1),
         "양호" if gene_data.COL10A1 >= age_avg.COL10A1 else "개선 필요"],
        ["탄력", 
         safe_format(gene_data.FLG),
         get_comparison_symbol(gene_data.FLG, overall_avg.FLG),
         "양호" if gene_data.FLG >= overall_avg.FLG else "개선 필요",
         get_comparison_symbol(gene_data.FLG, age_avg.FLG),
         "양호" if gene_data.FLG >= age_avg.FLG else "개선 필요"],
        ["수분", 
         safe_format(gene_data.AQP3),
         get_comparison_symbol(gene_data.AQP3, overall_avg.AQP3),
         "양호" if gene_data.AQP3 >= overall_avg.AQP3 else "개선 필요",
         get_comparison_symbol(gene_data.AQP3, age_avg.AQP3),
         "양호" if gene_data.AQP3 >= age_avg.AQP3 else "개선 필요"]
    ]

# 보고서 목록 표시
@main_bp.route('/reports')
def list_reports():
    """보고서 목록 페이지"""
    page = request.args.get("page", 1, type=int)
    per_page = 10
    with db.session() as session:
        try:
            paginated_users = session.query(User).order_by(User.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
            reports = [{"id": u.id, "name": u.name, "date": u.date.strftime('%Y%m%d')} for u in paginated_users.items]
            logger.info(f"Found {len(reports)} reports on page {page}")
            return render_template('reports.html', reports=reports, page=page, total_pages=paginated_users.pages)
        except Exception as e:
            logger.error(f"Error listing reports: {e}", exc_info=True)
            return render_template('error.html', message="보고서 목록을 불러오는 중 오류가 발생했습니다."), 500

# 보고서 삭제
@main_bp.route('/delete/<int:user_id>', methods=['POST'])
def delete_report(user_id):
    """보고서 삭제"""
    with db.session() as session:
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"error": "사용자를 찾을 수 없습니다."}), 404

            session.query(InputData).filter_by(user_id=user_id).delete()
            session.query(GeneData).filter_by(user_id=user_id).delete()
            session.delete(user)
            session.commit()

            # 차트 파일 삭제
            name = user.name
            date = user.date.strftime('%Y%m%d')
            radar_path = os.path.join(CHARTS_FOLDER, name, f"{name}_{date}_radar_chart.png")
            bar_path = os.path.join(CHARTS_FOLDER, name, f"{name}_{date}_bar_chart.png")
            if os.path.exists(radar_path):
                os.remove(radar_path)
            if os.path.exists(bar_path):
                os.remove(bar_path)

            return jsonify({"success": "보고서가 삭제되었습니다.", "redirect": url_for('main.list_reports')}), 200
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting report {user_id}: {e}", exc_info=True)
            return jsonify({"error": "삭제 중 오류가 발생했습니다."}), 500

# Flask 애플리케이션 실행
if __name__ == "__main__":
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Initializing fixed data...")
        initialize_fixed_data(db.session())
        logger.info("Application ready.")

    app.register_blueprint(main_bp)
    app.run(debug=True, host='0.0.0.0', port=5000)
