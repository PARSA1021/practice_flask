import os
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes

# 로깅 설정
logger = logging.getLogger(__name__)

CHARTS_FOLDER = os.path.join("static", "Charts", "user_charts")

def configure_matplotlib():
    """Matplotlib 기본 설정을 적용합니다."""
    rcParams['font.family'] = 'Malgun Gothic'
    rcParams['axes.unicode_minus'] = False

def get_chart_path(name, test_date, chart_type):
    """차트 파일 경로를 생성하고 디렉토리를 준비합니다."""
    file_name = f"{name}_{test_date.replace('-', '')}_{chart_type}.png"
    chart_path = os.path.join(CHARTS_FOLDER, name, file_name)
    os.makedirs(os.path.join(CHARTS_FOLDER, name), exist_ok=True)
    return file_name, chart_path

def radar_factory(num_vars, frame='circle'):
    """
    레이더 차트 축을 생성합니다.
    
    Args:
        num_vars (int): 변수 개수
        frame (str): 차트 모양 ('circle' 또는 'polygon')
    
    Returns:
        numpy.ndarray: 각도 배열
    """
    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False) + np.pi / 2
    class RadarAxes(PolarAxes):
        name = 'radar'
        RESOLUTION = 1
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.set_theta_zero_location('N')
        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)
            for label in self.get_xticklabels():
                label.set_fontsize(14)
                label.set_fontweight('bold')
                label.set_color('#333333')
    register_projection(RadarAxes)
    return theta

def plot_radar_chart(user_data, overall_avg, age_avg, name, test_date, check_exists=False):
    """
    사용자 데이터를 레이더 차트로 시각화합니다.
    
    Args:
        user_data: 사용자 유전자 데이터 객체
        overall_avg: 전체 평균 데이터 객체
        age_avg: 연령대 평균 데이터 객체
        name (str): 사용자 이름
        test_date (str): 검사 날짜 (YYYY-MM-DD)
        check_exists (bool): 기존 파일 확인 여부
    
    Returns:
        str: 생성된 차트 파일 이름
    """
    configure_matplotlib()
    categories = ['TIMP3', 'COL10A1', 'FLG', 'AQP3']
    labels = ['미백', '주름', '탄력', '수분']
    num_vars = len(categories)
    theta = radar_factory(num_vars)

    file_name, chart_path = get_chart_path(name, test_date, 'radar_chart')
    if check_exists and os.path.exists(chart_path):
        return file_name

    try:
        fig = plt.figure(figsize=(6, 6), facecolor='white')
        ax = fig.add_subplot(111, projection='radar')
        ax.set_facecolor('#F5F6F5')

        user_values = [user_data.TIMP3, user_data.COL10A1, user_data.FLG, user_data.AQP3]
        overall_values = [overall_avg.TIMP3, overall_avg.COL10A1, overall_avg.FLG, overall_avg.AQP3]
        age_values = [age_avg.TIMP3, age_avg.COL10A1, age_avg.FLG, age_avg.AQP3]

        ax.plot(theta, user_values, color='#1976D2', linewidth=3, linestyle='-', marker='o', markersize=8, alpha=0.9, label=name)
        ax.fill(theta, user_values, color='#1976D2', alpha=0.25)
        ax.plot(theta, overall_values, color='#F6AD55', linewidth=2, linestyle='--', label='전체 평균')
        ax.plot(theta, age_values, color='#38A169', linewidth=2, linestyle='--', label=f'{age_avg.age_group}대 평균')

        ax.grid(color='#D8D8D8', linestyle='-', linewidth=0.5, alpha=0.6)
        ax.set_yticklabels([])
        ax.set_varlabels(labels)
        ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=10)
        plt.tight_layout(pad=1.5)

        plt.savefig(chart_path, bbox_inches='tight', dpi=300, facecolor='white')
        plt.close()
        return file_name
    except Exception as e:
        logger.error(f"Failed to generate radar chart for {name}/{test_date}: {e}")
        raise

def plot_bar_chart(user_data, overall_avg, age_avg, name, test_date, check_exists=False):
    """
    사용자 데이터를 막대 차트로 시각화합니다.
    
    Args:
        user_data: 사용자 유전자 데이터 객체
        overall_avg: 전체 평균 데이터 객체
        age_avg: 연령대 평균 데이터 객체
        name (str): 사용자 이름
        test_date (str): 검사 날짜 (YYYY-MM-DD)
        check_exists (bool): 기존 파일 확인 여부
    
    Returns:
        str: 생성된 차트 파일 이름
    """
    configure_matplotlib()
    categories = ['TIMP3', 'COL10A1', 'FLG', 'AQP3']
    labels = ['미백', '주름', '탄력', '수분']
    num_vars = len(categories)

    file_name, chart_path = get_chart_path(name, test_date, 'bar_chart')
    if check_exists and os.path.exists(chart_path):
        return file_name

    try:
        user_values = [user_data.TIMP3, user_data.COL10A1, user_data.FLG, user_data.AQP3]
        overall_values = [overall_avg.TIMP3, overall_avg.COL10A1, overall_avg.FLG, overall_avg.AQP3]
        age_values = [age_avg.TIMP3, age_avg.COL10A1, age_avg.FLG, age_avg.AQP3]

        fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
        ax.set_facecolor('#F5F6F5')
        bar_width = 0.25
        index = np.arange(num_vars)

        ax.bar(index - bar_width, overall_values, bar_width, color='#F6AD55', label='전체 평균', alpha=0.9)
        ax.bar(index, user_values, bar_width, color='#1976D2', label=name, alpha=0.9)
        ax.bar(index + bar_width, age_values, bar_width, color='#38A169', label=f'{age_avg.age_group}대 평균', alpha=0.9)

        ax.grid(True, axis='y', color='#D8D8D8', linestyle='--', linewidth=0.5, alpha=0.6)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#D8D8D8')
        ax.set_xticks(index)
        ax.set_xticklabels(labels, fontsize=14, fontweight='bold', color='#333333')
        ax.set_yticklabels([])
        ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.05), fontsize=10)
        plt.tight_layout(pad=1.5)

        plt.savefig(chart_path, bbox_inches='tight', dpi=300, facecolor='white')
        plt.close()
        return file_name
    except Exception as e:
        logger.error(f"Failed to generate bar chart for {name}/{test_date}: {e}")
        raise