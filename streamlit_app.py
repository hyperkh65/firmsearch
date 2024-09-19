import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import re

# SSL/TLS 설정을 위한 어댑터 클래스
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.set_ciphers('DEFAULT:@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# 세션 생성 및 어댑터 설정
session = requests.Session()
session.mount('https://', TLSAdapter())

# 네이버 검색 결과에서 kiscode 추출 함수
def find_kiscode_from_naver_search(query):
    search_url = 'https://search.naver.com/search.naver'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    params = {
        'where': 'nexearch',
        'sm': 'top_hty',
        'fbm': '0',
        'ie': 'utf8',
        'query': query
    }

    try:
        response = session.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        more_info_link = soup.find('a', class_='info_more', href=True)
        if more_info_link and 'kiscode=' in more_info_link['href']:
            kiscode = re.search(r'kiscode=([A-Za-z0-9]+)', more_info_link['href'])
            if kiscode:
                return kiscode.group(1), more_info_link['href']
        return None, None
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return None, None

# 나이스 사이트에서 업체 정보를 가져오는 함수
def get_company_info(kiscode):
    url = f'https://www.nicebizinfo.com/ep/EP0100M002GE.nice?kiscode={kiscode}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        company_info = {
            '대표자': soup.find('p', string='대표자').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='대표자') else '-',
            '본사주소': soup.find('p', string='본사주소').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='본사주소') else '-',
            '그룹명': soup.find('p', string='그룹명').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='그룹명') else '-',
            '사업자번호': soup.find('p', string='사업자번호').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='사업자번호') else '-',
            '기업형태': soup.find('p', string='기업형태').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='기업형태') else '-',
            '산업': soup.find('p', string='산업').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='산업') else '-',
            '설립일자': soup.find('p', string='설립일자').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='설립일자') else '-',
            '상장일자': soup.find('p', string='상장일자').find_next_sibling('strong').get_text(strip=True) if soup.find('p', string='상장일자') else '-'
        }
        
        revenue_row = soup.find('tr', class_='bdBck fwb')
        if revenue_row:
            revenues = revenue_row.find_all('td', class_='tar')
            revenue_data = []
            for td in revenues:
                text = td.get_text(strip=True).replace(',', '').replace(' ', '')
                if text.isdigit():
                    revenue_data.append(f"{int(text) * 1000:,}")
                else:
                    revenue_data.append('-')
        else:
            revenue_data = ['-'] * 3
        
        return company_info, revenue_data
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return {}, ['-'] * 3

# 스트림릿 웹 앱 구성
def main():
    st.title("업체 정보 조회기")

    uploaded_file = st.file_uploader("업로드할 엑셀 파일을 선택하세요.", type=["xlsx"])
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        if '업체명' not in df.columns:
            st.error("엑셀 파일에 '업체명' 열이 존재하지 않습니다.")
            return
        
        results = []
        for company_name in df['업체명']:
            kiscode, nice_info_url = find_kiscode_from_naver_search(company_name)
            if kiscode:
                company_info, revenue_data = get_company_info(kiscode)
                result = {
                    '업체명': company_name,
                    'kiscode': kiscode,
                    '대표자': company_info.get('대표자', '-'),
                    '본사주소': company_info.get('본사주소', '-'),
                    '그룹명': company_info.get('그룹명', '-'),
                    '사업자번호': company_info.get('사업자번호', '-'),
                    '기업형태': company_info.get('기업형태', '-'),
                    '산업': company_info.get('산업', '-'),
                    '설립일자': company_info.get('설립일자', '-'),
                    '상장일자': company_info.get('상장일자', '-'),
                    '2023년 매출': revenue_data[0],
                    '2022년 매출': revenue_data[1],
                    '2021년 매출': revenue_data[2]
                }
                results.append(result)
            else:
                st.write(f"업체 '{company_name}'를 찾을 수 없습니다.")
        
        if results:
            results_df = pd.DataFrame(results)
            st.write(results_df)

if __name__ == "__main__":
    main()
