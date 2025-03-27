from flask import Blueprint, render_template, request, jsonify, url_for
import pandas as pd
import logging
from datetime import datetime
from process_data import save_to_db
from visualization import plot_radar_chart, plot_bar_chart
from ETC.Utils import get_comparison_symbol, safe_format
from ETC.Config import Session
from ETC.Data_Base_Model import User, InputData, GeneData, OverallAverageGeneData, AgeGroupAverageGeneData
import os

logger = logging.getLogger(__name__)

CHARTS_FOLDER = os.path.join("static", "charts")

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', today=datetime.now().strftime('%Y-%m-%d'))

@main_bp.route('/save', methods=['POST'])
def save_data():
    data = request.json
    required_fields = ["name", "birth_date", "test_date", "b_actin", "TIMP3", "COL10A1", "FLG", "AQP3"]
    
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        logger.warning(f"Missing fields: {missing_fields}")
        return jsonify({"error": f"다음 필수 항목을 입력해주세요: {', '.join(missing_fields)}"}), 400

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

    user_ids = save_to_db(input_df)
    if not user_ids:
        return jsonify({"error": "데이터 저장 실패 또는 중복 데이터입니다."}), 400

    session = Session()
    try:
        user = session.query(User).filter_by(id=user_ids[0]).first()
        gene_data = session.query(GeneData).filter_by(user_id=user_ids[0]).first()
        overall_avg = session.query(OverallAverageGeneData).first()
        age_avg = session.query(AgeGroupAverageGeneData).filter_by(age_group=user.age_group).first()

        name = input_df['이름'].iloc[0]
        test_date = input_df['날짜'].iloc[0].strftime('%Y-%m-%d')
        radar_chart = plot_radar_chart(gene_data, overall_avg, age_avg, name, test_date)
        bar_chart = plot_bar_chart(gene_data, overall_avg, age_avg, name, test_date)

        return jsonify({"report_url": url_for('main.serve_report', name=name, date=test_date.replace('-', ''))}), 200
    except Exception as e:
        logger.error(f"Error in save_data: {e}", exc_info=True)
        return jsonify({"error": "서버 오류가 발생했습니다. 다시 시도해주세요."}), 500
    finally:
        session.close()

@main_bp.route('/report/<name>/<date>')
def serve_report(name, date):
    session = Session()
    try:
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

        test_date = user.date
        radar_chart = plot_radar_chart(gene_data, overall_avg, age_avg, name, test_date, check_exists=True)
        bar_chart = plot_bar_chart(gene_data, overall_avg, age_avg, name, test_date, check_exists=True)

        gene_data_table = [
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

        report_data = {
            "name": name,
            "birth_date": user.birthdate,
            "test_date": test_date,
            "gene_data": [
                {"category": "대조군", "value": input_data.b_actin},
                {"category": "미백", "value": gene_data.TIMP3},
                {"category": "주름", "value": gene_data.COL10A1},
                {"category": "탄력", "value": gene_data.FLG},
                {"category": "수분", "value": gene_data.AQP3}
            ],
            "gene_data_table": gene_data_table,
            "radar_chart": radar_chart,
            "bar_chart": bar_chart
        }
        return render_template('report.html', **report_data)
    except Exception as e:
        logger.error(f"Error serving report: {e}", exc_info=True)
        return render_template('error.html', message="보고서 생성 중 오류가 발생했습니다."), 500
    finally:
        session.close()

@main_bp.route('/reports')
def list_reports():
    page = request.args.get("page", 1, type=int)
    per_page = 10
    session = Session()
    try:
        total = session.query(User).count()
        total_pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page

        users = session.query(User).order_by(User.date.desc()).limit(per_page).offset(offset).all()
        reports = [{"id": u.id, "name": u.name, "date": u.date.replace('-', '')} for u in users]
        logger.info(f"Found {len(reports)} reports on page {page}")
        return render_template('reports.html', reports=reports, page=page, total_pages=total_pages)
    except Exception as e:
        logger.error(f"Error listing reports: {e}", exc_info=True)
        return render_template('error.html', message="보고서 목록을 불러오는 중 오류가 발생했습니다."), 500
    finally:
        session.close()

@main_bp.route('/delete/<int:user_id>', methods=['POST'])
def delete_report(user_id):
    session = Session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "사용자를 찾을 수 없습니다."}), 404

        session.delete(user)  # CASCADE로 연관 데이터 삭제
        session.commit()

        name = user.name
        date = user.date.replace('-', '')
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
    finally:
        session.close()