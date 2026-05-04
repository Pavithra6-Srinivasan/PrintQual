"""
flask_app.py — Web interface for Life Test Data Analysis
Run on your own laptop: python flask_app.py
Browser opens automatically at http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, send_file
import threading
import uuid
import webbrowser
from pathlib import Path

from services.report_pipeline import ReportPipeline
from utils.paths import default_spec_path, default_output_dir

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max upload

UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Lazy — only created on first AI request so startup is instant
_ai_service = None

def get_ai_service():
    global _ai_service
    if _ai_service is None:
        from services.ai_service import AIService
        _ai_service = AIService()
    return _ai_service

jobs = {}   # job_id → Job instance


class Job:
    def __init__(self):
        self.status = 'running'   # running | done | error
        self.result = None
        self.error = None
        self.summary_text = None


def _run_pipeline(job_id, raw_file, output_folder):
    job = jobs[job_id]
    spec_file = str(default_spec_path()) if default_spec_path().exists() else None
    output_dir = output_folder or str(default_output_dir())

    try:
        result = ReportPipeline().run(
            raw_file=raw_file,
            spec_file=spec_file,
            output_folder=output_dir
        )
        job.result = result
        job.summary_text = result.get('summary_text', '')
        job.status = 'done'
    except Exception as exc:
        import traceback
        traceback.print_exc()
        job.error = str(exc)
        job.status = 'error'
    finally:
        Path(raw_file).unlink(missing_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    if 'raw_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f = request.files['raw_file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400

    job_id = str(uuid.uuid4())
    save_path = UPLOAD_FOLDER / f"{job_id}_{f.filename}"
    f.save(str(save_path))

    jobs[job_id] = Job()
    output_folder = request.form.get('output_folder', '').strip()

    threading.Thread(
        target=_run_pipeline,
        args=(job_id, str(save_path), output_folder),
        daemon=True
    ).start()

    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Not found'}), 404

    resp = {'status': job.status, 'error': job.error}

    if job.status == 'done' and job.result:
        r = job.result
        resp['result'] = {
            'printer':      r.get('printer', ''),
            'variant':      r.get('variant', ''),
            'sub_assembly': r.get('sub_assembly', ''),
            'quarter':      r.get('quarter', ''),
            'year':         r.get('year', ''),
            'excel_name':   Path(r['output_path']).name if r.get('output_path') else None,
            'pptx_name':    Path(r['pptx_path']).name if r.get('pptx_path') else None,
            'has_excel':    bool(r.get('output_path') and Path(r['output_path']).exists()),
            'has_pptx':     bool(r.get('pptx_path') and Path(r['pptx_path']).exists()),
        }

    return jsonify(resp)


@app.route('/download/<job_id>/<filetype>')
def download(job_id, filetype):
    job = jobs.get(job_id)
    if not job or job.status != 'done' or not job.result:
        return 'Not found', 404

    path = (job.result.get('output_path') if filetype == 'excel'
            else job.result.get('pptx_path'))

    if not path or not Path(path).exists():
        return 'File not found', 404

    return send_file(path, as_attachment=True)


@app.route('/ping')
def ping():
    resp = jsonify('ok')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json() or {}
    question = (data.get('question') or '').strip()
    job_id = data.get('job_id')

    if not question:
        return jsonify({'error': 'Empty question'}), 400

    job = jobs.get(job_id) if job_id else None
    summary = job.summary_text if job and job.summary_text else None

    trend_kw = {'quarter', 'trend', 'compare', 'history', 'over time', 'across'}
    is_trend = any(kw in question.lower() for kw in trend_kw)

    try:
        svc = get_ai_service()
        if is_trend:
            reply = svc.analyze_trends(question)
        elif summary:
            reply = svc.analyze_with_context(question, summary)
        else:
            reply = svc.answer_question(question)
        return jsonify({'response': reply})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


_LOADING_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Life Test Analysis — Starting…</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: #0d1117;
      color: #e6edf3;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }
    .card {
      text-align: center;
      padding: 48px 64px;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
    }
    h1 { font-size: 1.8rem; margin-bottom: 8px; }
    p  { color: #8b949e; margin-bottom: 32px; }
    .dots span {
      display: inline-block;
      width: 10px; height: 10px;
      margin: 0 4px;
      background: #1f6feb;
      border-radius: 50%;
      animation: bounce 1.2s infinite ease-in-out;
    }
    .dots span:nth-child(2) { animation-delay: .2s; }
    .dots span:nth-child(3) { animation-delay: .4s; }
    @keyframes bounce {
      0%,80%,100% { transform: scale(0); opacity:.4; }
      40%          { transform: scale(1); opacity:1; }
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Life Test Analysis</h1>
    <p>Starting up, please wait…</p>
    <div class="dots"><span></span><span></span><span></span></div>
  </div>
  <script>
    function check() {
      fetch('http://localhost:5000/ping', { mode: 'cors' })
        .then(function(r) {
          if (r.ok) { window.location.href = 'http://localhost:5000'; }
          else      { setTimeout(check, 500); }
        })
        .catch(function() { setTimeout(check, 500); });
    }
    setTimeout(check, 400);
  </script>
</body>
</html>"""


def _open_loading_page():
    import tempfile
    splash = Path(tempfile.gettempdir()) / 'printqual_loading.html'
    splash.write_text(_LOADING_HTML, encoding='utf-8')
    webbrowser.open(splash.as_uri())


if __name__ == '__main__':
    threading.Thread(target=_open_loading_page, daemon=True).start()
    app.run(host='localhost', port=5000, debug=False, threaded=True)
