import urllib.request
import ssl
import re
import json
import csv
import time
import html
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_TOPJOBS_CATEGORIES = {
    'SDQ': 'IT-Sware/DB/QA/Web/Graphics/GIS',
    'HNS': 'IT-HWare/Networks/Systems',
    'ACA': 'Accounting/Auditing/Finance',
    'BAF': 'Banking & Finance/Insurance',
    'SMM': 'Sales/Marketing/Merchandising',
    'HAT': 'HR/Training',
    'COM': 'Corporate Management/Analysts',
    'OAS': 'Office Admin/Secretary/Receptionist',
    'CCE': 'Civil Eng/Interior Design/Architecture',
    'ITT': 'IT-Telecoms',
    'CUR': 'Customer Relations/Public Relations',
    'LWT': 'Logistics/Warehouse/Transport',
    'MAE': 'Eng-Mech/Auto/Elec',
    'POS': 'Manufacturing/Operations',
    'MAC': 'Media/Advert/Communication',
    'HRF': 'Hotel/Restaurant/Hospitality',
    'HOT': 'Travel/Tourism',
    'MHN': 'Medical/Nursing/Healthcare',
    'LEL': 'Legal/Law',
    'SQC': 'Supervision/Quality Control',
    'APC': 'Apparel/Clothing',
    'AIM': 'Ticketing/Airline/Marine',
    'TAL': 'Education',
    'RLT': 'R&D/Science/Research',
    'AGD': 'Agriculture/Dairy/Environment',
    'SEC': 'Security',
    'BEC': 'Fashion/Design/Beauty',
    'IDV': 'International Development',
    'KPO': 'KPO/BPO',
    'IME': 'Imports/Exports'
}

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

class BaseScraper:
    def __init__(self):
        self.headers = DEFAULT_HEADERS.copy()
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE


class TopJobsScraper(BaseScraper):
    BASE_URL = "https://www.topjobs.lk"
    LIST_URL = "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp"

    def _fetch_html(self, url: str, retries: int = 3, timeout: int = 20) -> str:
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, context=self.ctx, timeout=timeout) as resp:
                    return resp.read().decode('utf-8', errors='ignore')
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(0.5)

    def get_categories(self) -> Dict[str, str]:
        try:
            html_content = self._fetch_html(self.LIST_URL, retries=2, timeout=8)
            soup = BeautifulSoup(html_content, 'html.parser')
            categories = {}
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'FA=' in href:
                    match = re.search(r'FA=([A-Z0-9]+)', href)
                    if match:
                        code = match.group(1)
                        name = a.get_text(strip=True)
                        if name and code not in categories and name != 'View As Grid':
                            categories[code] = name
            if categories:
                return categories
        except Exception:
            pass
        return DEFAULT_TOPJOBS_CATEGORIES.copy()

    def scrape(
        self,
        category_code: str = 'SDQ',
        category_name: str = '',
        deep_scrape: bool = False,
        progress_callback: Optional[Callable[[int, str, int, int], None]] = None
    ) -> List[Dict]:
        if not category_name:
            category_name = DEFAULT_TOPJOBS_CATEGORIES.get(category_code, category_code)

        if progress_callback:
            progress_callback(10, f"Connecting to TopJobs.lk [{category_code}]...", 0, 0)

        url = f"{self.LIST_URL}?FA={category_code}"
        html_content = self._fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        rows = soup.find_all('tr')
        job_rows = []
        for tr in rows:
            onclick = tr.get('onclick', '')
            if 'createAlert' in onclick or tr.find('span', id=re.compile(r'^hdnJC')):
                tds = tr.find_all('td')
                if len(tds) >= 5:
                    job_rows.append(tr)

        total_jobs = len(job_rows)
        if progress_callback:
            progress_callback(25, f"TopJobs: Found {total_jobs} listings. Extracting...", 0, total_jobs)

        jobs = []
        for i, tr in enumerate(job_rows):
            onclick = tr.get('onclick', '')
            tds = tr.find_all('td')

            rid, agent_code, job_code, emp_code = "", "", "", ""
            params = re.findall(r"'([^']*)'", onclick)
            if len(params) >= 4:
                rid = params[0]
                agent_code = params[1]
                job_code = params[2]
                emp_code = params[3]

            ref_no = tds[1].get_text(strip=True) if len(tds) > 1 else job_code.lstrip('0')

            title_td = tds[2]
            h2 = title_td.find('h2')
            title = h2.get_text(strip=True) if h2 else ""
            h1 = title_td.find('h1')
            employer = h1.get_text(strip=True) if h1 else ""

            desc_snippet = tds[3].get_text(strip=True) if len(tds) > 3 else ""
            opening_date = tds[4].get_text(strip=True) if len(tds) > 4 else ""
            closing_date = tds[5].get_text(strip=True) if len(tds) > 5 else ""
            town = tds[6].get_text(strip=True) if len(tds) > 6 else ""

            detail_url = ""
            if job_code:
                detail_url = f"{self.BASE_URL}/employer/JobAdvertismentServlet?rid={rid or '0'}&ac={agent_code}&jc={job_code}&ec={emp_code}&pg=applicant/vacancybyfunctionalarea.jsp"

            job_data = {
                "source": "TopJobs.lk",
                "ref_no": ref_no or "TJ-" + (job_code or str(i+1)),
                "title": title,
                "employer": employer,
                "category_code": category_code,
                "category_name": category_name,
                "description_snippet": desc_snippet,
                "opening_date": opening_date,
                "closing_date": closing_date,
                "town": town,
                "job_type": "Full-Time / General",
                "salary": "Negotiable / See Advert",
                "detail_url": detail_url or self.BASE_URL,
                "logo_url": ""
            }

            if deep_scrape and detail_url:
                try:
                    d_html = self._fetch_html(detail_url, retries=1, timeout=5)
                    d_soup = BeautifulSoup(d_html, 'html.parser')
                    job_data["detail_text"] = d_soup.get_text(separator="\n", strip=True)[:1500]
                    for img in d_soup.find_all('img'):
                        src = img.get('src', '')
                        if '/logo/' in src:
                            if src.startswith('/'):
                                src = f"{self.BASE_URL}{src}"
                            job_data["logo_url"] = src
                            break
                except Exception:
                    pass

            jobs.append(job_data)

            if progress_callback and total_jobs > 0:
                pct = 25 + int(((i + 1) / total_jobs) * 75)
                progress_callback(pct, f"TopJobs: Processing advert {i+1}/{total_jobs}...", i+1, total_jobs)

        return jobs


class XpressJobsScraper(BaseScraper):
    API_URL = "https://xpress.jobs/api/jobs/searchJobs"
    VIEW_BASE = "https://xpress.jobs/jobs/view/"

    def scrape(
        self,
        pages: int = 3,
        progress_callback: Optional[Callable[[int, str, int, int], None]] = None
    ) -> List[Dict]:
        if progress_callback:
            progress_callback(10, "Connecting to XpressJobs.lk API...", 0, 0)

        jobs = []
        headers = self.headers.copy()
        headers['Accept'] = 'application/json'

        for p in range(1, pages + 1):
            if progress_callback:
                progress_callback(10 + (p * 20), f"XpressJobs: Fetching page {p}/{pages}...", p, pages)
            try:
                res = requests.get(f"{self.API_URL}?page={p}&pageSize=35", headers=headers, timeout=8, verify=False)
                if res.status_code == 200 and isinstance(res.json(), list):
                    raw_items = res.json()
                    for item in raw_items:
                        job_id = item.get('jobId')
                        title = item.get('jobTitle', '')
                        employer = item.get('organizationName', '')
                        locations = item.get('locations', '').strip()
                        job_type = item.get('jobType', '')
                        overview = item.get('overview', '')
                        logo = item.get('logoImageUrl', '')
                        expiry = item.get('expiryDateOnWebsite', '')
                        if expiry and 'T' in expiry:
                            expiry = expiry.split('T')[0]

                        detail_url = f"{self.VIEW_BASE}{job_id}" if job_id else "https://xpress.jobs"

                        jobs.append({
                            "source": "XpressJobs.lk",
                            "ref_no": f"XJ-{job_id}",
                            "title": title,
                            "employer": employer,
                            "category_code": "XJ",
                            "category_name": "General / Various",
                            "description_snippet": overview,
                            "opening_date": "Recently Posted",
                            "closing_date": expiry or "N/A",
                            "town": locations or "Sri Lanka",
                            "job_type": job_type or "Full-Time",
                            "salary": "See Advert",
                            "detail_url": detail_url,
                            "logo_url": logo or ""
                        })
            except Exception:
                break

        if progress_callback:
            progress_callback(100, f"XpressJobs: Extracted {len(jobs)} jobs.", len(jobs), len(jobs))

        return jobs


class RoosterJobsScraper(BaseScraper):
    GRAPHQL_URL = "https://api.rooster.jobs/core/graphql"

    def scrape(
        self,
        max_companies: int = 30,
        progress_callback: Optional[Callable[[int, str, int, int], None]] = None
    ) -> List[Dict]:
        if progress_callback:
            progress_callback(10, "Connecting to Rooster.jobs GraphQL API...", 0, 0)

        jobs = []
        seen_ids = set()

        query = '''
        query FetchJobs($cid: ID!) {
          fetchAllJobsPublicFiltered(companyId: $cid, page: 1, limit: 30) {
            jobs {
              id
              title
              jobType
              location
              department
              createdAt
              remote
              formattedAddress
            }
          }
        }
        '''
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/json'

        def fetch_company(cid):
            try:
                payload = {"query": query, "variables": {"cid": str(cid)}}
                res = requests.post(self.GRAPHQL_URL, json=payload, headers=headers, timeout=3)
                if res.status_code == 200:
                    data = res.json().get('data', {})
                    if data and 'fetchAllJobsPublicFiltered' in data:
                        return cid, data['fetchAllJobsPublicFiltered'].get('jobs', [])
            except Exception:
                pass
            return cid, []

        if progress_callback:
            progress_callback(20, "Rooster.jobs: Querying company directory in parallel...", 0, max_companies)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_company, cid) for cid in range(1, max_companies + 1)]
            done_count = 0
            for future in as_completed(futures):
                done_count += 1
                cid, raw_jobs = future.result()
                for j in raw_jobs:
                    jid = j.get('id')
                    if not jid or jid in seen_ids:
                        continue
                    seen_ids.add(jid)

                    title = j.get('title', '')
                    job_type = j.get('jobType', '')
                    loc = j.get('formattedAddress') or j.get('location') or 'Sri Lanka'
                    dept = j.get('department') or 'General'
                    remote = " (Remote)" if j.get('remote') else ""

                    created_ts = j.get('createdAt')
                    created_date = "Recently"
                    if created_ts and isinstance(created_ts, (int, float)):
                        try:
                            created_date = time.strftime('%Y-%m-%d', time.localtime(created_ts / 1000))
                        except Exception:
                            pass

                    jobs.append({
                        "source": "Rooster.jobs",
                        "ref_no": f"RJ-{jid}",
                        "title": title,
                        "employer": f"Company #{cid}",
                        "category_code": "RJ",
                        "category_name": dept,
                        "description_snippet": f"Department: {dept}. Mode: {job_type}{remote}.",
                        "opening_date": created_date,
                        "closing_date": "Open",
                        "town": loc,
                        "job_type": f"{job_type.title()}{remote}",
                        "salary": "See Advert",
                        "detail_url": f"https://rooster.jobs/job/{jid}",
                        "logo_url": ""
                    })

                if progress_callback and done_count % 5 == 0:
                    pct = 20 + int((done_count / max_companies) * 75)
                    progress_callback(pct, f"Rooster.jobs: Processed {done_count}/{max_companies} companies...", done_count, max_companies)

        if progress_callback:
            progress_callback(100, f"Rooster.jobs: Extracted {len(jobs)} active listings.", len(jobs), len(jobs))

        return jobs


class JobpalScraper(BaseScraper):
    AJAX_URL = "https://jobpal.lk/jm-ajax/get_listings/"

    def scrape(
        self,
        max_pages: int = 3,
        progress_callback: Optional[Callable[[int, str, int, int], None]] = None
    ) -> List[Dict]:
        if progress_callback:
            progress_callback(10, "Connecting to Jobpal.lk AJAX endpoint...", 0, 0)

        jobs = []
        headers = self.headers.copy()
        headers['X-Requested-With'] = 'XMLHttpRequest'

        for p in range(1, max_pages + 1):
            if progress_callback:
                pct = 10 + int((p / max_pages) * 80)
                progress_callback(pct, f"Jobpal.lk: Fetching page {p}/{max_pages}...", p, max_pages)

            try:
                res = requests.post(self.AJAX_URL, data={'per_page': 40, 'page': p}, headers=headers, timeout=8)
                if res.status_code == 200:
                    html_data = res.json().get('html', '')
                    soup = BeautifulSoup(html_data, 'html.parser')
                    listings = soup.find_all('li', class_=re.compile(r'job_listing'))
                    if not listings:
                        break

                    for li in listings:
                        job_id = li.get('id', '').replace('job_listing-', '')
                        detail_url = li.get('data-href') or ""
                        if not detail_url:
                            a_click = li.find('a', class_='job_listing-clickbox')
                            if a_click and a_click.get('href'):
                                detail_url = a_click['href']

                        title_el = li.find(class_='job_listing-title') or li.find('h3')
                        title = title_el.get_text(strip=True) if title_el else ""

                        comp_el = li.find(class_='job_listing-company') or li.find(class_='company')
                        employer = comp_el.get_text(strip=True) if comp_el else ""

                        sal_el = li.find(class_='job_listing-salary')
                        salary = sal_el.get_text(strip=True) if sal_el else "Negotiable"

                        loc_el = li.find(class_='job_listing-location') or li.find(class_='location')
                        location = loc_el.get_text(strip=True) if loc_el else "Sri Lanka"

                        type_el = li.find(class_='job_listing-type') or li.find(class_='job-type')
                        job_type = type_el.get_text(strip=True) if type_el else "Full-Time"

                        date_el = li.find(class_='job_listing-date') or li.find('date')
                        date_posted = date_el.get_text(strip=True) if date_el else "Recently"

                        img_el = li.find('img', class_='company_logo')
                        logo_url = img_el.get('src', '') if img_el else ""

                        if title:
                            jobs.append({
                                "source": "Jobpal.lk",
                                "ref_no": f"JP-{job_id}" if job_id else f"JP-{len(jobs)+1}",
                                "title": title,
                                "employer": employer or "Direct Employer",
                                "category_code": "JP",
                                "category_name": "General / Local",
                                "description_snippet": f"Position: {title}. Salary: {salary}.",
                                "opening_date": date_posted,
                                "closing_date": "Open",
                                "town": location,
                                "job_type": job_type.title(),
                                "salary": salary,
                                "detail_url": detail_url or "https://jobpal.lk",
                                "logo_url": logo_url
                            })
            except Exception:
                break

        if progress_callback:
            progress_callback(100, f"Jobpal.lk: Extracted {len(jobs)} jobs.", len(jobs), len(jobs))

        return jobs


class ObserverJobsScraper(BaseScraper):
    VACANCIES_URL = "https://observerjobs.lk/vacancies"

    def scrape(
        self,
        max_pages: int = 3,
        progress_callback: Optional[Callable[[int, str, int, int], None]] = None
    ) -> List[Dict]:
        if progress_callback:
            progress_callback(10, "Connecting to ObserverJobs.lk...", 0, 0)

        jobs = []

        for p in range(1, max_pages + 1):
            if progress_callback:
                pct = 10 + int((p / max_pages) * 80)
                progress_callback(pct, f"ObserverJobs.lk: Fetching page {p}/{max_pages}...", p, max_pages)

            try:
                url = f"{self.VACANCIES_URL}?page={p}"
                res = requests.get(url, headers=self.headers, timeout=8)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    app_div = soup.find(id='app')
                    if app_div and app_div.has_attr('data-page'):
                        page_data = json.loads(html.unescape(app_div['data-page']))
                        props = page_data.get('props', {})
                        results = props.get('results', {}) or props.get('jobs', {})
                        raw_items = results.get('data', [])

                        if not raw_items:
                            break

                        for item in raw_items:
                            jid = item.get('id')
                            title = item.get('title', '')
                            slug = item.get('slug', '')

                            comp_info = item.get('company', {}) or {}
                            employer = comp_info.get('name', 'Sri Lanka Employer')
                            logo = comp_info.get('logo_url', '')

                            cats = item.get('categories', [])
                            cat_name = cats[0].get('name') if cats and isinstance(cats, list) else "Observer Category"

                            salary = item.get('salary', '')
                            salary_str = f"Rs. {salary}" if salary and salary != "0" else ("Negotiable" if item.get('negotiable') else "See Advert")

                            loc = item.get('location', '') or "Sri Lanka"
                            jtype = item.get('type', '') or "Full time"
                            deadline = item.get('deadline', '') or "N/A"
                            created = item.get('created_at', '') or "Recently"

                            detail_url = f"https://observerjobs.lk/vacancy/{jid}/{slug}" if jid else "https://observerjobs.lk"

                            jobs.append({
                                "source": "ObserverJobs.lk",
                                "ref_no": f"OJ-{jid}",
                                "title": title,
                                "employer": employer,
                                "category_code": "OJ",
                                "category_name": cat_name,
                                "description_snippet": f"Category: {cat_name}. Industry: {comp_info.get('industry', 'General')}.",
                                "opening_date": created,
                                "closing_date": deadline,
                                "town": loc,
                                "job_type": jtype.title(),
                                "salary": salary_str,
                                "detail_url": detail_url,
                                "logo_url": logo
                            })
            except Exception:
                break

        if progress_callback:
            progress_callback(100, f"ObserverJobs.lk: Extracted {len(jobs)} jobs.", len(jobs), len(jobs))

        return jobs


class MultiSourceJobScraper:
    SOURCES = {
        'ALL': 'All Portals (Combined)',
        'topjobs': 'TopJobs.lk',
        'xpressjobs': 'XpressJobs.lk',
        'rooster': 'Rooster.jobs',
        'jobpal': 'Jobpal.lk',
        'observerjobs': 'ObserverJobs.lk'
    }

    def __init__(self):
        self.topjobs = TopJobsScraper()
        self.xpressjobs = XpressJobsScraper()
        self.rooster = RoosterJobsScraper()
        self.jobpal = JobpalScraper()
        self.observerjobs = ObserverJobsScraper()

    def get_sources(self) -> Dict[str, str]:
        return self.SOURCES.copy()

    def get_topjobs_categories(self) -> Dict[str, str]:
        return self.topjobs.get_categories()

    def scrape(
        self,
        source_key: str = 'ALL',
        category_code: str = 'SDQ',
        deep_scrape: bool = False,
        progress_callback: Optional[Callable[[int, str, int, int], None]] = None
    ) -> List[Dict]:
        source_key = source_key.lower() if source_key else 'all'
        all_results = []

        if source_key == 'topjobs':
            cat_name = DEFAULT_TOPJOBS_CATEGORIES.get(category_code, category_code)
            all_results.extend(self.topjobs.scrape(category_code, cat_name, deep_scrape, progress_callback))

        elif source_key == 'xpressjobs':
            all_results.extend(self.xpressjobs.scrape(pages=3, progress_callback=progress_callback))

        elif source_key == 'rooster':
            all_results.extend(self.rooster.scrape(max_companies=30, progress_callback=progress_callback))

        elif source_key == 'jobpal':
            all_results.extend(self.jobpal.scrape(max_pages=3, progress_callback=progress_callback))

        elif source_key == 'observerjobs':
            all_results.extend(self.observerjobs.scrape(max_pages=3, progress_callback=progress_callback))

        elif source_key == 'all':
            scrapers = [
                ('TopJobs.lk', lambda cb: self.topjobs.scrape(category_code, DEFAULT_TOPJOBS_CATEGORIES.get(category_code, category_code), deep_scrape, cb)),
                ('XpressJobs.lk', lambda cb: self.xpressjobs.scrape(pages=2, progress_callback=cb)),
                ('Rooster.jobs', lambda cb: self.rooster.scrape(max_companies=20, progress_callback=cb)),
                ('Jobpal.lk', lambda cb: self.jobpal.scrape(max_pages=2, progress_callback=cb)),
                ('ObserverJobs.lk', lambda cb: self.observerjobs.scrape(max_pages=2, progress_callback=cb)),
            ]

            if progress_callback:
                progress_callback(10, "Starting fast parallel scrape across 5 portals...", 0, 5)

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fn, None): sname for sname, fn in scrapers}
                done_count = 0
                for future in as_completed(futures):
                    sname = futures[future]
                    done_count += 1
                    try:
                        res = future.result()
                        all_results.extend(res)
                        if progress_callback:
                            pct = 10 + int((done_count / 5) * 85)
                            progress_callback(pct, f"[{sname}] Extracted {len(res)} jobs ({done_count}/5 portals completed)", done_count, 5)
                    except Exception as e:
                        if progress_callback:
                            progress_callback(int((done_count / 5) * 85), f"[{sname}] Error: {str(e)}", done_count, 5)

            if progress_callback:
                progress_callback(100, f"Combined scrape completed! {len(all_results)} jobs extracted across 5 portals.", len(all_results), len(all_results))

        else:
            raise ValueError(f"Unknown source portal key: {source_key}")

        return all_results

    @staticmethod
    def export_to_json(jobs: List[Dict], filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        print(f"Exported {len(jobs)} jobs to {filepath}")

    @staticmethod
    def export_to_csv(jobs: List[Dict], filepath: str):
        if not jobs:
            print("No jobs to export.")
            return

        all_keys = list(jobs[0].keys())
        for j in jobs:
            for k in j.keys():
                if k not in all_keys:
                    all_keys.append(k)

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            for job in jobs:
                row = job.copy()
                for k, v in row.items():
                    if isinstance(v, list):
                        row[k] = "; ".join(map(str, v))
                writer.writerow(row)
        print(f"Exported {len(jobs)} jobs to {filepath}")
