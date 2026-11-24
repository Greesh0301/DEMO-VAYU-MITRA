import argparse
import base64
from email.parser import BytesParser
from email.policy import default as email_default_policy
import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import Config, FRONTEND_DIR, UPLOAD_FOLDER
from services import (
    COMMUNITY_CATEGORIES,
    REPORT_STATUSES,
    add_exposure_diary_entry,
    add_personal_activity,
    add_personal_location,
    create_community_report,
    create_contact_message,
    delete_personal_activity,
    delete_personal_location,
    export_air_twin_csv,
    export_reports_csv,
    get_air_quality_data,
    get_air_twin_data,
    get_alerts_data,
    get_auth_session,
    get_clean_routes,
    get_community_contribution_summary,
    get_dashboard_data,
    get_forecast_data,
    get_india_locations_directory,
    get_insights_data,
    get_profile_bundle,
    get_reports_data,
    get_time_machine_data,
    init_db,
    list_community_reports,
    login_user,
    logout_user,
    register_user,
    simulate_what_if,
    update_community_report_status,
    update_profile_bundle,
)

init_db()


def _parse_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_int(val):
    if val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _parse_bool(val):
    if val is None:
        return False
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _extract_auth_token_from_headers(headers) -> str:
    auth_hdr = headers.get("Authorization") or ""
    if auth_hdr.lower().startswith("bearer "):
        return auth_hdr[7:].strip()
    x_tok = headers.get("X-Auth-Token") or ""
    if x_tok:
        return x_tok.strip()
    return ""


def create_flask_app():
    from flask import Flask, Response, jsonify, request, send_from_directory
    from flask_cors import CORS

    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_UPLOAD_BYTES
    CORS(app)

    @app.route("/")
    def serve_index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:filename>")
    def serve_frontend(filename):
        target = os.path.join(FRONTEND_DIR, filename)
        if os.path.isfile(target):
            return send_from_directory(FRONTEND_DIR, filename)
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    @app.route("/api/dashboard", methods=["GET"])
    def api_dashboard():
        try:
            city = request.args.get("city")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            return jsonify(get_dashboard_data(city=city, lat=lat, lon=lon))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Live air quality data unavailable: {exc}"}), 502

    @app.route("/api/locations/india", methods=["GET"])
    def api_india_locations():
        return jsonify(get_india_locations_directory())

    @app.route("/api/air-quality", methods=["GET"])
    def api_air_quality():
        try:
            city = request.args.get("city")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            return jsonify(get_air_quality_data(city=city, lat=lat, lon=lon))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Air quality service unavailable: {exc}"}), 502

    @app.route("/api/air-quality/forecast", methods=["GET"])
    def api_forecast():
        try:
            city = request.args.get("city")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            return jsonify(get_forecast_data(city=city, lat=lat, lon=lon))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Forecast service unavailable: {exc}"}), 502

    @app.route("/api/air-quality/history", methods=["GET"])
    def api_history():
        try:
            city = request.args.get("city")
            period = request.args.get("period", "daily")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")
            return jsonify(get_reports_data(city=city, period=period, lat=lat, lon=lon, start_date=start_date, end_date=end_date))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Historical data unavailable: {exc}"}), 502

    @app.route("/api/insights", methods=["GET"])
    def api_insights():
        try:
            city = request.args.get("city")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            return jsonify(get_insights_data(city=city, lat=lat, lon=lon))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Insights service unavailable: {exc}"}), 502

    @app.route("/api/insights/time-machine", methods=["GET"])
    def api_time_machine():
        try:
            city = request.args.get("city")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            target_date = request.args.get("target_date")
            compare_date = request.args.get("compare_date")
            return jsonify(get_time_machine_data(city=city, lat=lat, lon=lon, target_date=target_date, compare_date=compare_date))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Time Machine archive unavailable: {exc}"}), 502

    @app.route("/api/insights/simulate", methods=["POST"])
    def api_simulate():
        try:
            data = request.get_json(silent=True) or {}
            res = simulate_what_if(
                city=data.get("city"),
                lat=_parse_float(data.get("lat")),
                lon=_parse_float(data.get("lon")),
                traffic_reduction_pct=float(data.get("traffic_reduction_pct", 0)),
                dust_control_pct=float(data.get("dust_control_pct", 0)),
                greenery_increase_pct=float(data.get("greenery_increase_pct", 0)),
                burning_reduction_pct=float(data.get("burning_reduction_pct", 0)),
                industrial_reduction_pct=float(data.get("industrial_reduction_pct", 0)),
            )
            return jsonify(res)
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Simulation failed: {exc}"}), 502

    @app.route("/api/routes", methods=["GET"])
    def api_routes():
        try:
            origin = request.args.get("origin", "")
            destination = request.args.get("destination", "")
            mode = request.args.get("mode", "walking")
            escape_mode = _parse_bool(request.args.get("escape_mode"))
            return jsonify(get_clean_routes(origin=origin, destination=destination, mode=mode, escape_mode=escape_mode))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Route planner unavailable: {exc}"}), 502

    @app.route("/api/alerts", methods=["GET"])
    def api_alerts():
        try:
            city = request.args.get("city")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            return jsonify(get_alerts_data(city=city, lat=lat, lon=lon))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Alerts service unavailable: {exc}"}), 502

    @app.route("/api/reports", methods=["GET"])
    def api_reports():
        try:
            city = request.args.get("city")
            period = request.args.get("period", "daily")
            lat = _parse_float(request.args.get("lat"))
            lon = _parse_float(request.args.get("lon"))
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")
            compare_city = request.args.get("compare_city")
            return jsonify(get_reports_data(city=city, period=period, lat=lat, lon=lon, start_date=start_date, end_date=end_date, compare_city=compare_city))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": f"Reports unavailable: {exc}"}), 502

    @app.route("/api/reports/export", methods=["GET"])
    def api_reports_export():
        try:
            city = request.args.get("city")
            period = request.args.get("period", "daily")
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")
            filename, csv_text = export_reports_csv(city=city, period=period, start_date=start_date, end_date=end_date)
            return Response(
                csv_text,
                mimetype="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": f"Export failed: {exc}"}), 502

    @app.route("/api/community/reports", methods=["GET"])
    def api_community_reports():
        status = request.args.get("status")
        category = request.args.get("category")
        search = request.args.get("search")
        return jsonify(
            {
                "categories": COMMUNITY_CATEGORIES,
                "statuses": REPORT_STATUSES,
                "contribution_summary": get_community_contribution_summary(),
                "reports": list_community_reports(status=status, category=category, search=search),
            }
        )

    @app.route("/api/community/report", methods=["POST"])
    def api_community_report():
        try:
            if request.content_type and "multipart/form-data" in request.content_type:
                title = request.form.get("title", "")
                description = request.form.get("description", "")
                category = request.form.get("category", "")
                location_name = request.form.get("location_name", "")
                lat = _parse_float(request.form.get("latitude"))
                lon = _parse_float(request.form.get("longitude"))
                photo = request.files.get("photo")
                file_bytes = photo.read() if photo and photo.filename else None
                orig_name = photo.filename if photo and photo.filename else None
            else:
                data = request.get_json(silent=True) or {}
                title = data.get("title", "")
                description = data.get("description", "")
                category = data.get("category", "")
                location_name = data.get("location_name", "")
                lat = _parse_float(data.get("latitude"))
                lon = _parse_float(data.get("longitude"))
                file_bytes = None
                orig_name = data.get("photo_name")
                if data.get("photo_base64"):
                    b64_str = data["photo_base64"].split(",")[-1]
                    file_bytes = base64.b64decode(b64_str)

            created = create_community_report(
                title=title,
                description=description,
                category=category,
                location_name=location_name,
                latitude=lat,
                longitude=lon,
                file_bytes=file_bytes,
                original_filename=orig_name,
            )
            return jsonify({"message": "Community report submitted successfully.", "report": created}), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": f"Unable to save report: {exc}"}), 500

    @app.route("/api/community/reports/<int:report_id>/status", methods=["PUT", "PATCH"])
    def api_community_report_status(report_id):
        try:
            data = request.get_json(silent=True) or {}
            updated = update_community_report_status(report_id, data.get("status", ""))
            return jsonify({"report": updated})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.route("/api/auth/login", methods=["POST"])
    def api_auth_login():
        try:
            data = request.get_json(silent=True) or {}
            res = login_user(data.get("email", ""), data.get("password", ""))
            return jsonify(res)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 401
        except Exception as exc:
            return jsonify({"error": f"Login failed: {exc}"}), 500

    @app.route("/api/auth/register", methods=["POST"])
    def api_auth_register():
        try:
            data = request.get_json(silent=True) or {}
            res = register_user(
                data.get("name", ""),
                data.get("email", ""),
                data.get("password", ""),
                data.get("preferred_city", "Mumbai"),
            )
            return jsonify(res), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": f"Registration failed: {exc}"}), 500

    @app.route("/api/auth/logout", methods=["POST"])
    def api_auth_logout():
        token = _extract_auth_token_from_headers(request.headers)
        return jsonify(logout_user(token))

    @app.route("/api/auth/me", methods=["GET"])
    def api_auth_me():
        token = _extract_auth_token_from_headers(request.headers)
        return jsonify(get_auth_session(token))

    @app.route("/api/profile", methods=["GET", "PUT"])
    def api_profile():
        token = _extract_auth_token_from_headers(request.headers)
        if request.method == "GET":
            return jsonify(get_profile_bundle(auth_token=token))
        try:
            data = request.get_json(silent=True) or {}
            updated = update_profile_bundle(data, auth_token=token)
            return jsonify({"message": "Settings saved successfully.", **updated})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": f"Failed to update settings: {exc}"}), 500

    @app.route("/api/air-twin", methods=["GET"])
    def api_air_twin():
        try:
            token = _extract_auth_token_from_headers(request.headers)
            return jsonify(get_air_twin_data(include_live=True, auth_token=token))
        except Exception as exc:
            return jsonify({"error": f"Air Twin service error: {exc}"}), 502

    @app.route("/api/air-twin/locations", methods=["POST"])
    def api_air_twin_add_location():
        try:
            token = _extract_auth_token_from_headers(request.headers)
            data = request.get_json(silent=True) or {}
            created = add_personal_location(
                data.get("label", ""),
                data.get("city", ""),
                hours_per_day=float(data.get("hours_per_day", 8.0) or 8.0),
                auth_token=token,
            )
            return jsonify({"message": "Frequent location added.", "location": created}), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.route("/api/air-twin/locations/<int:loc_id>", methods=["DELETE"])
    def api_air_twin_del_location(loc_id):
        try:
            delete_personal_location(loc_id)
            return jsonify({"message": "Location removed."})
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.route("/api/air-twin/activities", methods=["POST"])
    def api_air_twin_add_activity():
        try:
            token = _extract_auth_token_from_headers(request.headers)
            data = request.get_json(silent=True) or {}
            created = add_personal_activity(
                activity_type=data.get("activity_type", ""),
                location_id=_parse_int(data.get("location_id")),
                hours_per_day=float(data.get("hours_per_day", 1)),
                intensity=data.get("intensity", "Moderate"),
                is_outdoor=bool(data.get("is_outdoor", True)),
                auth_token=token,
            )
            return jsonify({"message": "Daily activity logged.", "activity": created}), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/air-twin/activities/<int:act_id>", methods=["DELETE"])
    def api_air_twin_del_activity(act_id):
        try:
            delete_personal_activity(act_id)
            return jsonify({"message": "Activity removed."})
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.route("/api/air-twin/diary", methods=["POST"])
    def api_air_twin_add_diary():
        try:
            token = _extract_auth_token_from_headers(request.headers)
            data = request.get_json(silent=True) or {}
            entry = add_exposure_diary_entry(notes=data.get("notes", ""), entry_date=data.get("entry_date"), auth_token=token)
            return jsonify({"message": "Exposure diary snapshot logged.", "entry": entry}), 201
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/air-twin/export", methods=["GET"])
    def api_air_twin_export():
        try:
            fname, csv_text = export_air_twin_csv()
            return Response(
                csv_text,
                mimetype="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            )
        except Exception as exc:
            return jsonify({"error": f"Export failed: {exc}"}), 500

    @app.route("/api/contact", methods=["POST"])
    def api_contact():
        try:
            data = request.get_json(silent=True) or {}
            saved = create_contact_message(
                name=data.get("name", ""),
                email=data.get("email", ""),
                subject=data.get("subject", "General Feedback"),
                message=data.get("message", ""),
            )
            return jsonify({"message": "Thank you for contacting VayuMitra.", "ticket": saved}), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    return app


def run_stdlib_server(host: str, port: int):
    """Pure-Python stdlib HTTP server fallback when Flask is not installed in the host environment."""

    class VayuMitraHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send_json(self, status_code: int, payload):
            body = json.dumps(payload).encode("utf-8")
            try:
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except BrokenPipeError:
                pass

        def _send_bytes(self, status_code: int, content_type: str, data: bytes, extra_headers=None):
            try:
                self.send_response(status_code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                if extra_headers:
                    for k, v in extra_headers.items():
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)
            except BrokenPipeError:
                pass

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            return self.rfile.read(length) if length > 0 else b""

        @staticmethod
        def _parse_multipart(ctype: str, raw: bytes):
            header_bytes = f"Content-Type: {ctype}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
            msg = BytesParser(policy=email_default_policy).parsebytes(header_bytes + raw)
            fields = {}
            files = {}
            if msg.is_multipart():
                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    if not name:
                        continue
                    filename = part.get_filename()
                    payload = part.get_payload(decode=True) or b""
                    if filename:
                        files[name] = (filename, payload)
                    else:
                        fields[name] = payload.decode("utf-8", errors="replace")
            return fields, files

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)
            q = lambda key, default=None: qs.get(key, [default])[0]

            try:
                if path == "/api/dashboard":
                    return self._send_json(200, get_dashboard_data(q("city"), _parse_float(q("lat")), _parse_float(q("lon"))))
                if path == "/api/locations/india":
                    return self._send_json(200, get_india_locations_directory())
                if path == "/api/air-quality":
                    return self._send_json(200, get_air_quality_data(q("city"), _parse_float(q("lat")), _parse_float(q("lon"))))
                if path == "/api/air-quality/forecast":
                    return self._send_json(200, get_forecast_data(q("city"), _parse_float(q("lat")), _parse_float(q("lon"))))
                if path == "/api/air-quality/history":
                    return self._send_json(
                        200,
                        get_reports_data(
                            q("city"),
                            q("period", "daily"),
                            _parse_float(q("lat")),
                            _parse_float(q("lon")),
                            q("start_date"),
                            q("end_date"),
                        ),
                    )
                if path == "/api/insights":
                    return self._send_json(200, get_insights_data(q("city"), _parse_float(q("lat")), _parse_float(q("lon"))))
                if path == "/api/insights/time-machine":
                    return self._send_json(
                        200,
                        get_time_machine_data(
                            q("city"),
                            _parse_float(q("lat")),
                            _parse_float(q("lon")),
                            q("target_date"),
                            q("compare_date"),
                        ),
                    )
                if path == "/api/routes":
                    return self._send_json(
                        200,
                        get_clean_routes(
                            q("origin", ""),
                            q("destination", ""),
                            q("mode", "walking"),
                            _parse_bool(q("escape_mode")),
                        ),
                    )
                if path == "/api/alerts":
                    return self._send_json(200, get_alerts_data(q("city"), _parse_float(q("lat")), _parse_float(q("lon"))))
                if path == "/api/reports":
                    return self._send_json(
                        200,
                        get_reports_data(
                            q("city"),
                            q("period", "daily"),
                            _parse_float(q("lat")),
                            _parse_float(q("lon")),
                            q("start_date"),
                            q("end_date"),
                            q("compare_city"),
                        ),
                    )
                if path == "/api/reports/export":
                    fname, csv_text = export_reports_csv(q("city"), q("period", "daily"), q("start_date"), q("end_date"))
                    return self._send_bytes(
                        200,
                        "text/csv; charset=utf-8",
                        csv_text.encode("utf-8"),
                        {"Content-Disposition": f'attachment; filename="{fname}"'},
                    )
                if path == "/api/community/reports":
                    return self._send_json(
                        200,
                        {
                            "categories": COMMUNITY_CATEGORIES,
                            "statuses": REPORT_STATUSES,
                            "contribution_summary": get_community_contribution_summary(),
                            "reports": list_community_reports(q("status"), q("category"), q("search")),
                        },
                    )
                if path == "/api/auth/me":
                    tok = _extract_auth_token_from_headers(self.headers)
                    return self._send_json(200, get_auth_session(tok))
                if path == "/api/profile":
                    tok = _extract_auth_token_from_headers(self.headers)
                    return self._send_json(200, get_profile_bundle(auth_token=tok))
                if path == "/api/air-twin":
                    tok = _extract_auth_token_from_headers(self.headers)
                    return self._send_json(200, get_air_twin_data(include_live=True, auth_token=tok))
                if path == "/api/air-twin/export":
                    fname, csv_text = export_air_twin_csv()
                    return self._send_bytes(
                        200,
                        "text/csv; charset=utf-8",
                        csv_text.encode("utf-8"),
                        {"Content-Disposition": f'attachment; filename="{fname}"'},
                    )

                if path.startswith("/uploads/"):
                    fname = os.path.basename(path[len("/uploads/"):])
                    fpath = os.path.join(UPLOAD_FOLDER, fname)
                    if os.path.isfile(fpath):
                        ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
                        with open(fpath, "rb") as fh:
                            return self._send_bytes(200, ctype, fh.read())
                    return self._send_json(404, {"error": "File not found."})

                rel = "index.html" if path in ("", "/") else path.lstrip("/")
                fpath = os.path.normpath(os.path.join(FRONTEND_DIR, rel))
                if not fpath.startswith(os.path.abspath(FRONTEND_DIR)) or not os.path.isfile(fpath):
                    fpath = os.path.join(FRONTEND_DIR, "index.html")
                ctype = mimetypes.guess_type(fpath)[0] or "text/html; charset=utf-8"
                with open(fpath, "rb") as fh:
                    return self._send_bytes(200, ctype, fh.read())
            except ValueError as exc:
                return self._send_json(400, {"error": str(exc)})
            except LookupError as exc:
                return self._send_json(404, {"error": str(exc)})
            except Exception as exc:
                return self._send_json(502, {"error": str(exc)})

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            try:
                if path == "/api/insights/simulate":
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    res = simulate_what_if(
                        city=data.get("city"),
                        lat=_parse_float(data.get("lat")),
                        lon=_parse_float(data.get("lon")),
                        traffic_reduction_pct=float(data.get("traffic_reduction_pct", 0)),
                        dust_control_pct=float(data.get("dust_control_pct", 0)),
                        greenery_increase_pct=float(data.get("greenery_increase_pct", 0)),
                        burning_reduction_pct=float(data.get("burning_reduction_pct", 0)),
                        industrial_reduction_pct=float(data.get("industrial_reduction_pct", 0)),
                    )
                    return self._send_json(200, res)

                if path == "/api/auth/login":
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    try:
                        return self._send_json(200, login_user(data.get("email", ""), data.get("password", "")))
                    except ValueError as exc:
                        return self._send_json(401, {"error": str(exc)})

                if path == "/api/auth/register":
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    return self._send_json(
                        201,
                        register_user(
                            data.get("name", ""),
                            data.get("email", ""),
                            data.get("password", ""),
                            data.get("preferred_city", "Mumbai"),
                        ),
                    )

                if path == "/api/auth/logout":
                    tok = _extract_auth_token_from_headers(self.headers)
                    return self._send_json(200, logout_user(tok))

                if path == "/api/air-twin/locations":
                    tok = _extract_auth_token_from_headers(self.headers)
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    created = add_personal_location(
                        data.get("label", ""),
                        data.get("city", ""),
                        hours_per_day=float(data.get("hours_per_day", 8.0) or 8.0),
                        auth_token=tok,
                    )
                    return self._send_json(201, {"message": "Frequent location added.", "location": created})

                if path == "/api/air-twin/activities":
                    tok = _extract_auth_token_from_headers(self.headers)
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    created = add_personal_activity(
                        activity_type=data.get("activity_type", ""),
                        location_id=_parse_int(data.get("location_id")),
                        hours_per_day=float(data.get("hours_per_day", 1)),
                        intensity=data.get("intensity", "Moderate"),
                        is_outdoor=bool(data.get("is_outdoor", True)),
                        auth_token=tok,
                    )
                    return self._send_json(201, {"message": "Daily activity logged.", "activity": created})

                if path == "/api/air-twin/diary":
                    tok = _extract_auth_token_from_headers(self.headers)
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    entry = add_exposure_diary_entry(notes=data.get("notes", ""), entry_date=data.get("entry_date"), auth_token=tok)
                    return self._send_json(201, {"message": "Exposure diary snapshot logged.", "entry": entry})

                if path == "/api/community/report":
                    ctype = self.headers.get("Content-Type", "")
                    raw = self._read_body()
                    if len(raw) > Config.MAX_UPLOAD_BYTES + 65536:
                        return self._send_json(413, {"error": "Payload exceeds maximum upload limit (5 MB)."})
                    if "multipart/form-data" in ctype:
                        fields, files = self._parse_multipart(ctype, raw)
                        title = fields.get("title", "")
                        desc = fields.get("description", "")
                        cat = fields.get("category", "")
                        loc = fields.get("location_name", "")
                        lat = _parse_float(fields.get("latitude"))
                        lon = _parse_float(fields.get("longitude"))
                        file_bytes = None
                        orig_name = None
                        if "photo" in files:
                            orig_name, file_bytes = files["photo"]
                    else:
                        data = json.loads(raw.decode("utf-8") or "{}")
                        title = data.get("title", "")
                        desc = data.get("description", "")
                        cat = data.get("category", "")
                        loc = data.get("location_name", "")
                        lat = _parse_float(data.get("latitude"))
                        lon = _parse_float(data.get("longitude"))
                        file_bytes = None
                        orig_name = data.get("photo_name")
                        if data.get("photo_base64"):
                            file_bytes = base64.b64decode(data["photo_base64"].split(",")[-1])

                    created = create_community_report(title, desc, cat, loc, lat, lon, file_bytes, orig_name)
                    return self._send_json(201, {"message": "Community report submitted successfully.", "report": created})

                if path == "/api/contact":
                    data = json.loads(self._read_body().decode("utf-8") or "{}")
                    saved = create_contact_message(data.get("name", ""), data.get("email", ""), data.get("subject", "General Feedback"), data.get("message", ""))
                    return self._send_json(201, {"message": "Thank you for contacting VayuMitra.", "ticket": saved})

                return self._send_json(404, {"error": "Endpoint not found."})
            except ValueError as exc:
                return self._send_json(400, {"error": str(exc)})
            except LookupError as exc:
                return self._send_json(404, {"error": str(exc)})
            except Exception as exc:
                return self._send_json(500, {"error": str(exc)})

        def do_DELETE(self):
            path = urllib.parse.urlparse(self.path).path
            try:
                if path.startswith("/api/air-twin/locations/"):
                    lid = int(path.strip("/").split("/")[-1])
                    delete_personal_location(lid)
                    return self._send_json(200, {"message": "Location removed."})
                if path.startswith("/api/air-twin/activities/"):
                    aid = int(path.strip("/").split("/")[-1])
                    delete_personal_activity(aid)
                    return self._send_json(200, {"message": "Activity removed."})
                return self._send_json(404, {"error": "Endpoint not found."})
            except LookupError as exc:
                return self._send_json(404, {"error": str(exc)})
            except Exception as exc:
                return self._send_json(500, {"error": str(exc)})

        def do_PUT(self):
            self._handle_update()

        def do_PATCH(self):
            self._handle_update()

        def _handle_update(self):
            path = urllib.parse.urlparse(self.path).path
            try:
                data = json.loads(self._read_body().decode("utf-8") or "{}")
                if path == "/api/profile":
                    tok = _extract_auth_token_from_headers(self.headers)
                    return self._send_json(200, {"message": "Settings saved successfully.", **update_profile_bundle(data, auth_token=tok)})
                if path.startswith("/api/community/reports/") and path.endswith("/status"):
                    parts = path.strip("/").split("/")
                    rid = int(parts[3])
                    return self._send_json(200, {"report": update_community_report_status(rid, data.get("status", ""))})
                return self._send_json(404, {"error": "Endpoint not found."})
            except ValueError as exc:
                return self._send_json(400, {"error": str(exc)})
            except LookupError as exc:
                return self._send_json(404, {"error": str(exc)})
            except Exception as exc:
                return self._send_json(500, {"error": str(exc)})

    server = ThreadingHTTPServer((host, port), VayuMitraHandler)
    print(f"VayuMitra stdlib backend listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VayuMitra Environmental Platform Server")
    parser.add_argument("--host", default=Config.HOST)
    parser.add_argument("--port", type=int, default=Config.PORT)
    parser.add_argument("--stdlib", action="store_true", help="Run built-in Python stdlib HTTP mode")
    args = parser.parse_args()

    if args.stdlib:
        run_stdlib_server(args.host, args.port)
    else:
        try:
            flask_app = create_flask_app()
            flask_app.run(host=args.host, port=args.port, debug=Config.DEBUG)
        except ImportError:
            run_stdlib_server(args.host, args.port)
