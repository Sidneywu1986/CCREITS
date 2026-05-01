# -*- coding: utf-8 -*-
"""
REITs 分红公告 PDF 自动下载器（直连交易所）
"""

import requests
import pandas as pd
import os
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./reits_dividend_downloader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class REITsDividendPDFDownloader:
    """REITs 分红公告 PDF 自动下载器"""
    
    def __init__(self, base_path: str = "./reits_dividend_pdfs"):
        self.base_path = base_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.download_delay = 2.0
        self.downloaded_log = self._load_download_log()
        os.makedirs(self.base_path, exist_ok=True)
    
    def _load_download_log(self) -> set:
        """加载已下载文件记录"""
        log_file = os.path.join(self.base_path, ".download_log.txt")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        return set()
    
    def _save_download_log(self, file_identifier: str):
        """记录已下载文件"""
        log_file = os.path.join(self.base_path, ".download_log.txt")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{file_identifier}\n")
        self.downloaded_log.add(file_identifier)
    
    def _sanitize_filename(self, title: str, max_length: int = 50) -> str:
        """清理文件名非法字符"""
        safe = re.sub(r'[\\/*?:"<>|]', "", title)
        safe = re.sub(r'\s+', "_", safe)
        if len(safe) > max_length:
            safe = safe[:max_length] + "..."
        return safe
    
    def _generate_filepath(self, row: pd.Series) -> tuple:
        """生成文件存储路径和唯一标识"""
        fund_code = str(row['fund_code'])
        publish_date = str(row['publish_date']).replace('-', '')
        title = row['title']
        ann_id = str(row['announcement_id'])
        
        safe_title = self._sanitize_filename(title)
        filename = f"{fund_code}_{publish_date}_{safe_title}_{ann_id}.pdf"
        
        subdir = os.path.join(self.base_path, fund_code)
        os.makedirs(subdir, exist_ok=True)
        
        filepath = os.path.join(subdir, filename)
        file_id = f"{fund_code}_{ann_id}_{publish_date}"
        
        return filepath, file_id
    
    def _download_single(self, url: str, filepath: str, file_id: str, timeout: int = 30) -> Dict:
        """下载单个 PDF"""
        result = {
            'success': False,
            'filepath': filepath,
            'file_id': file_id,
            'url': url,
            'error': None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_size': 0
        }
        
        # 检查是否已下载
        if file_id in self.downloaded_log:
            if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
                logger.info(f"[SKIP] 已存在: {os.path.basename(filepath)}")
                result['success'] = True
                result['file_size'] = os.path.getsize(filepath)
                return result
        
        if not url or not url.startswith(('http://', 'https://')):
            result['error'] = f"无效 URL: {url}"
            logger.error(f"[ERROR] {file_id}: {result['error']}")
            return result
        
        try:
            # 区分交易所添加 Referer
            if 'sse.com.cn' in url:
                headers = {'Referer': 'http://www.sse.com.cn/assortment/fund/reits/home/'}
            elif 'szse.cn' in url:
                headers = {'Referer': 'http://www.szse.cn/market/fund/reits/bulletin/'}
            else:
                headers = {}
            
            logger.info(f"[DOWNLOAD] {file_id} -> {os.path.basename(filepath)}")
            
            resp = self.session.get(
                url, 
                headers=headers, 
                timeout=timeout, 
                stream=True,
                allow_redirects=True
            )
            resp.raise_for_status()
            
            # 流式下载
            downloaded_size = 0
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            # 验证文件大小
            if downloaded_size < 1024:
                result['error'] = f"文件过小 ({downloaded_size} bytes)"
                logger.error(f"[ERROR] {file_id}: {result['error']}")
                os.remove(filepath)
                return result
            
            result['success'] = True
            result['file_size'] = downloaded_size
            self._save_download_log(file_id)
            logger.info(f"[SUCCESS] {file_id}: {downloaded_size/1024:.1f} KB")
            
            time.sleep(self.download_delay)
            
        except Exception as e:
            result['error'] = f"异常: {str(e)}"
            logger.error(f"[ERROR] {file_id}: {result['error']}")
        
        return result
    
    def batch_download(self, df: pd.DataFrame) -> pd.DataFrame:
        """批量下载 DataFrame 中的 PDF"""
        if df.empty:
            logger.warning("输入 DataFrame 为空")
            return pd.DataFrame()
        
        required_cols = ['fund_code', 'announcement_id', 'publish_date', 'title', 'url']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"缺少必要字段: {missing}")
        
        results = []
        total = len(df)
        
        logger.info(f"开始批量下载，共 {total} 个文件")
        
        for idx, row in df.iterrows():
            logger.info(f"[{idx+1}/{total}] 处理 {row['fund_code']}...")
            
            filepath, file_id = self._generate_filepath(row)
            url = row['url']
            
            result = self._download_single(url, filepath, file_id)
            results.append(result)
        
        result_df = pd.DataFrame(results)
        success_count = result_df['success'].sum()
        logger.info(f"下载完成: 成功 {success_count}/{total}")
        
        return result_df


if __name__ == "__main__":
    logger.info("REITs分红PDF下载器 - 与dividend_crawler配合使用")
    logger.info("Usage: 先运行dividend_crawler获取公告列表，再使用本下载器")
