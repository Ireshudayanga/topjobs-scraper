# Sri Lanka Multi-Portal Job Scraper & Interactive Map Dashboard

A powerful Python web scraper, REST/GraphQL API aggregator, and interactive web dashboard featuring a **live Sri Lanka Map** for collecting and exploring active job opportunities across Sri Lanka's top 5 job portals:
- **TopJobs.lk**
- **XpressJobs.lk**
- **Rooster.jobs**
- **Jobpal.lk**
- **ObserverJobs.lk**

---

## 🌟 Key Features.
- 🗺️ **Sri Lanka Interactive Job Map**: Built-in Leaflet.js dark map displaying district & location job markers with real-time job density counts across Sri Lanka.
- 🎯 **Map-based Location Selection**: Click any district pin (Colombo, Gampaha, Kandy, Galle, Jaffna, Kurunegala, Matara, etc.) to instantly filter the dashboard job listings table!
- 🔄 **Dynamic Synchronized Filters**: Map numbers & badges automatically update whenever you search, change source portals, or filter categories.
- 🌐 **5 Top Sri Lankan Portals**: Combined or portal-specific scraping.
- 🚀 **Real-time Event Streaming**: Progress feedback bar in Web UI via Server-Sent Events (SSE).
- 📊 **Comprehensive Fields**: Source Portal, Job Ref #, Position Title, Employer / Company, Category / Industry, Job Type / Work Mode, Location / Town, Posted Date, Closing Date / Deadline, Salary, Overview / Description, Logo URL, Direct Advert URL.
- 👁️ **Interactive Details Modal**: Pop-up view for full job summaries, salary breakdown, contact info, and employer details.
- 📁 **Export Capabilities**: Export job results to **CSV** or **JSON** with a single click.
- 💻 **CLI & Web Dashboard**: Full Command-line interface + Web UI.

---

## 📁 Project Structure
```
topjobs-scraper/
├── scraper.py          # Modular multi-source scrapers & manager class
├── web_app.py          # Flask Web Dashboard server with SSE streaming
├── cli.py              # CLI tool for scraping any or all portals
├── templates/
│   └── index.html      # Glassmorphism dark mode Web UI + Leaflet Sri Lanka Map
└── README.md           # Documentation
```

---

## 🚀 1. Using the Web Dashboard (Recommended)

Start the Flask web server:
```bash
python3 web_app.py
```
Open your browser at **[http://localhost:3000](http://localhost:3000)**.

### Features in Web UI:
- **Sri Lanka Interactive Map**: Zoom & pan across Sri Lanka districts. Click any marker badge (e.g. `Colombo (125)`, `Kandy (24)`) to filter listings by that district.
- **Portal Selection Tabs**: Scrape All 5 Portals combined or select an individual portal (`TopJobs.lk`, `XpressJobs.lk`, `Rooster.jobs`, `Jobpal.lk`, `ObserverJobs.lk`).
- **Category Filter**: Select any TopJobs functional area.
- **Deep Scraping**: Option to fetch deep detail pages & banner image URLs.
- **Interactive Details Modal**: View full advert details, employer logo, salary info, and opening/closing dates.
- **Instant Search & Export**: Real-time filtering and 1-click **Export to CSV** / **Export to JSON**.

---

## 💻 2. Using the CLI Tool

List supported job portals:
```bash
python3 cli.py --list-sources
```

List available TopJobs category codes:
```bash
python3 cli.py --list-categories
```

Scrape all 5 job portals combined:
```bash
python3 cli.py --source ALL --output all_srilanka_jobs.csv
```

Scrape a specific portal:
```bash
# Scrape XpressJobs.lk
python3 cli.py --source xpressjobs --output xpress_jobs.json

# Scrape Rooster.jobs
python3 cli.py --source rooster --output rooster_jobs.json

# Scrape Jobpal.lk
python3 cli.py --source jobpal --output jobpal_jobs.csv

# Scrape ObserverJobs.lk
python3 cli.py --source observerjobs --output observer_jobs.json

# Scrape TopJobs.lk IT category
python3 cli.py --source topjobs --category SDQ --output topjobs_it.csv
```

---

## 🐍 3. Python API Usage

```python
from scraper import MultiSourceJobScraper

scraper = MultiSourceJobScraper()

# 1. List supported sources
sources = scraper.get_sources()
print("Supported Sources:", sources)

# 2. Scrape all portals combined
all_jobs = scraper.scrape(source_key='ALL')

# 3. Scrape specific portal (e.g. XpressJobs)
xpress_jobs = scraper.scrape(source_key='xpressjobs')

# 4. Export data
scraper.export_to_csv(all_jobs, 'sri_lanka_job_opportunities.csv')
scraper.export_to_json(all_jobs, 'sri_lanka_job_opportunities.json')
```

---

## 📋 Standardized Fields Column Schema

| Column Name | Example | Description |
|-------------|---------|-------------|
| `source` | `XpressJobs.lk` | Portal name (`TopJobs.lk`, `XpressJobs.lk`, `Rooster.jobs`, `Jobpal.lk`, `ObserverJobs.lk`) |
| `ref_no` | `XJ-336527` | Unique reference / Job ID |
| `title` | `Showroom Sales Executive` | Job Position Title |
| `employer` | `CyberDeals` | Employer / Organization Name |
| `category_name` | `Sales/Marketing/Merchandising` | Functional Area / Industry Category |
| `job_type` | `Full-Time (Remote)` | Employment Type (Full-Time, Part-Time, Contract, Internship, Remote) |
| `town` | `Colombo, Western Province` | City, Town, or Region |
| `opening_date` | `2026-09-30` | Date job posting opened / created |
| `closing_date` | `2026-10-14` | Expiry / Deadline date |
| `salary` | `Rs. 150,000 - 200,000` | Salary range or Negotiable tag |
| `description_snippet` | `Experienced candidates & freshers welcome...` | Brief overview / description |
| `detail_url` | `https://xpress.jobs/jobs/view/336527` | Direct link to view advertisement |
| `logo_url` | `https://cdn.xpress.jobs/Organizations/logo_18714.png` | Employer / Company logo URL |
