from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from scraper import MultiSourceJobScraper
import io
import csv
import json
import queue
import threading

app = Flask(__name__)
scraper = MultiSourceJobScraper()

SOURCES_CACHE = scraper.get_sources()
CATEGORIES_CACHE = scraper.get_topjobs_categories()

@app.route('/')
def index():
    return render_template(
        'index.html', 
        sources=SOURCES_CACHE, 
        categories=CATEGORIES_CACHE
    )

@app.route('/api/sources')
def get_sources():
    return jsonify(SOURCES_CACHE)

@app.route('/api/categories')
def get_categories():
    return jsonify(CATEGORIES_CACHE)

@app.route('/api/scrape')
def scrape_json():
    """Direct REST JSON endpoint (fallback & fast fetch)."""
    source_key = request.args.get('source', 'ALL').lower()
    cat_code = request.args.get('category', 'SDQ').upper()
    deep = request.args.get('deep', 'false').lower() == 'true'
    
    try:
        jobs = scraper.scrape(
            source_key=source_key,
            category_code=cat_code,
            deep_scrape=deep
        )
        return jsonify({
            'status': 'success',
            'type': 'complete',
            'source': source_key,
            'category_code': cat_code,
            'count': len(jobs),
            'jobs': jobs
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'type': 'error',
            'message': str(e)
        }), 500

@app.route('/api/scrape_stream')
def scrape_stream():
    source_key = request.args.get('source', 'ALL').lower()
    cat_code = request.args.get('category', 'SDQ').upper()
    deep = request.args.get('deep', 'false').lower() == 'true'

    def event_stream():
        yield ": ping\n\n"
        
        q = queue.Queue()

        def progress_callback(percent, msg, current, total):
            q.put({
                'type': 'progress',
                'percent': percent,
                'message': msg,
                'current': current,
                'total': total
            })

        def run_scrape():
            try:
                jobs = scraper.scrape(
                    source_key=source_key,
                    category_code=cat_code,
                    deep_scrape=deep,
                    progress_callback=progress_callback
                )
                q.put({
                    'type': 'complete',
                    'status': 'success',
                    'source': source_key,
                    'category_code': cat_code,
                    'count': len(jobs),
                    'jobs': jobs
                })
            except Exception as e:
                q.put({
                    'type': 'error',
                    'message': str(e)
                })

        thread = threading.Thread(target=run_scrape, daemon=True)
        thread.start()

        while True:
            try:
                item = q.get(timeout=25)
                data = json.dumps(item)
                yield f"data: {data}\n\n"
                if item.get('type') in ['complete', 'error']:
                    break
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/export/csv')
def export_csv():
    source_key = request.args.get('source', 'ALL').lower()
    cat_code = request.args.get('category', 'SDQ').upper()
    jobs = scraper.scrape(source_key=source_key, category_code=cat_code, deep_scrape=False)

    output = io.StringIO()
    if jobs:
        all_keys = list(jobs[0].keys())
        for j in jobs:
            for k in j.keys():
                if k not in all_keys:
                    all_keys.append(k)

        writer = csv.DictWriter(output, fieldnames=all_keys)
        writer.writeheader()
        for job in jobs:
            row = job.copy()
            for k, v in row.items():
                if isinstance(v, list):
                    row[k] = "; ".join(map(str, v))
            writer.writerow(row)

    filename = f"job_opportunities_{source_key}_{cat_code}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@app.route('/api/export/json')
def export_json():
    source_key = request.args.get('source', 'ALL').lower()
    cat_code = request.args.get('category', 'SDQ').upper()
    jobs = scraper.scrape(source_key=source_key, category_code=cat_code, deep_scrape=False)

    filename = f"job_opportunities_{source_key}_{cat_code}.json"
    return Response(
        json.dumps(jobs, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

if __name__ == '__main__':
    print("Starting Multi-Portal Job Scraper Web Dashboard on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000, debug=False, threaded=True)
