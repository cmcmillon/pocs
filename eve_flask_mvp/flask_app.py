from flask import Flask, jsonify, abort, render_template, request, redirect, \
    url_for, send_from_directory, session, escape

import os
from werkzeug.utils import secure_filename
import pandas as pd
import sys
import webbrowser
import jinja2
from jinja2 import escape
from flask_caching import Cache

app = Flask(__name__)
#path = 'C:' + "\employment\eve_flask_mvp"
path = os.path.abspath("uploads")
app.config['UPLOAD_FOLDER'] = os.path.join(path)
app.config['ALLOWED_EXTENSIONS'] = set(['csv'])


cache_path = os.path.abspath("caching_directory")
print("cache_path: %s" % cache_path)

config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "filesystem", # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 3000,
    "CACHE_IGNORE_ERRORS": 0,
    "CACHE_THRESHOLD": 20,
    "CACHE_DIR": cache_path
}
#app = Flask(__name__)
# tell Flask to use the above defined config
app.config.from_mapping(config)

cache = Cache(app)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def set_template(tmpl_filename=None, from_string=None):
    """
    receives a template filename or file as string;
    attempts to return a template object
    """
    # Set the relative template path
    template_loader = jinja2.FileSystemLoader(searchpath="./templates")
    if from_string and not tmpl_filename:
        template_env = jinja2.Environment(loader=template_loader).from_string(from_string)
        tmpl_obj = template_env
    if tmpl_filename and not from_string:
        template_env = jinja2.Environment(loader=template_loader)
        tmpl_obj = template_env.get_template(tmpl_filename)

    return tmpl_obj

@app.route("/", methods=['GET'])
@app.route("/flask_mvp/upload_display", methods=['GET'])
def upload_display():
    """
    diplays uploaded files
    """
    return upload_display_action(optional_display=0)


def upload_display_action(optional_display=0):
    """
    build the upload Display
    """
    download_route = "/flask_mvp/downloads/"
    csv_display_route = "/flask_mvp/load_csv/"
    filenames = os.listdir(app.config['UPLOAD_FOLDER'])
    # set template for All uploaded files
    rendered_row_str = ""
    for file_link in filenames:
        file_download_url = download_route + file_link
        csv_display_url = csv_display_route + file_link
        uploaded_files_obj = set_template("links.html")
        link_dict = {"href_download": file_download_url, "href_download_file": file_link,
                     "href_csv_display": csv_display_url, "href_csv_file": "View CSV"}
        rendered_html =  uploaded_files_obj.render(link_dict)
        rendered_row_str += rendered_html
    uploaded_files_display_obj = set_template("upload_display.html")
    if optional_display:
        rendered_html = \
        uploaded_files_display_obj.render({"files_uploads": rendered_row_str})
    else:
        rendered_html = \
            uploaded_files_display_obj.render({"files_uploads": rendered_row_str,
                            "csv_filename": " ", "csv_table": " ",
                            "csv_stat_table": " "
                            })
    return rendered_html


@app.route("/flask_mvp/upload_action", methods=['POST','GET'])
def upload_action():
    """
    uploads a file
    """
    uploaded_files = request.files.getlist("file[]")
    filenames = []
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            print("file: %s" % str(file))
            filenames.append(filename)
    # This line is essential, store the data in session
    #session['filenames'] = filenames
    return render_template(os.path.join("upload.html"), filenames=filenames)


@app.route('/flask_mvp/downloads/<filename>')
def uploaded(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)


@app.route("/flask_mvp/load_csv/<filename>", methods=['GET'])
@cache.cached(timeout=5000)
def load_csv(filename):
    """
    sends a csv to the browser
    """
    return load_csv_action(filename)


def load_csv_action(filename, csv_stats=0):
    """
    creates the csv for the browser
    """
    csv_2_display = os.path.join(app.config['UPLOAD_FOLDER'],filename)
    trimmed_df = pd.read_csv(csv_2_display)

    print("def len: %s" % str(len(trimmed_df.index)))

    grouped_df = ""
    if csv_stats:
        grouped_df = trimmed_df.groupby("date", sort=True)["name"].count()
        path = os.path.abspath("grouped.csv")
        grouped_df.to_csv(path)
        grouped_df = pd.read_csv(path)

    html_data = trimmed_df.to_html()

    html_data = html_data.replace("dataframe","inlineTable")
    if csv_stats:
        html_data = html_data + " " + '\n'+ 'csv_stat_table'
        path = os.path.abspath('test_data.html')
        with open(path, 'w') as f:
            f.write(str(html_data))

    path = os.path.abspath('data.html')

    print("path: %s" % str(path))
    url = 'file://' + path
    with open(path, 'w') as f:
        f.write(html_data)

    # set template and add table to it
    upload_display_tmpl_str = upload_display_action(optional_display=1)
    csv_display_obj = set_template(None, from_string=upload_display_tmpl_str)

    csv_data_dict = {"csv_table": html_data,
                     "csv_filename": "current csv: "+filename,
                     "csv_file": filename
                    }
    output_text = csv_display_obj.render(csv_data_dict)

    if csv_stats:
        return output_text, grouped_df
    else:
        return output_text


@app.route('/flask_mvp/load_csv_stats/<filename>', methods=['GET'])
@cache.cached(timeout=5000)
def load_csv_stats(filename):
    """
    renders stats on the current dataframe
    """
    return load_csv_stats_action(filename)


def load_csv_stats_action(filename):
    """
    creates stats for the current dataframe
    """
    csv_text_tmpl_str, grouped_df = load_csv_action(filename, csv_stats=1)
    csv_text_tmpl_str = csv_text_tmpl_str.replace("csv_stat_table","{{csv_stat_table}}")
    csv_text_obj = set_template(None, from_string=csv_text_tmpl_str)

    html_data = grouped_df.to_html()
    html_data = html_data.replace("dataframe",'inlineTable" valign="top')

    path = os.path.abspath('test_data2.html')
    with open(path, 'w') as f:
        f.write(str(html_data))

    csv_stats_dict = {"csv_stat_table": html_data}
    output_text = csv_text_obj.render(csv_stats_dict)

    return output_text


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int("5000"), debug=True)
