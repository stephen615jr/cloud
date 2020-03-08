import json
import os
import shutil

from flask import Flask, redirect, render_template, request
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename

from app.utils import add_to_hides, gen_random_password, get_hides, remove_from_hides

from .config import cfg
from .forms import UploadForm
from .utils import get_folders, get_sudoers, get_user, log

app = Flask(__name__)
app.secret_key = gen_random_password()
Bootstrap(app)

META = '<meta http-equiv="refresh" content="3;url=/files">'
META2 = '<meta http-equiv="refresh" content="5;url=/files">'


@app.route("/", methods=["GET"])
def index():
    form = UploadForm()

    folder_choices = get_folders()
    form.folder.choices = [(i, x.as_posix()) for i, x in enumerate(folder_choices)]

    log("User %r opened index", get_user())
    return render_template("minimal.html", form=form)


@app.route("/upload", methods=["POST"])
def upload():
    form = UploadForm()

    if form.folder.data is None:
        return (
            f"{META2}<h1>No folder supplied or an invalid folder was supplied<h1>",
            400,
        )

    folder_choices = get_folders()

    try:
        folder = folder_choices[int(form.folder.data)]
    except IndexError:
        return f"{META2}<h1>Invalid index folder<h2>", 400
    files = request.files.getlist("files")

    if not files:
        return f"{META2}<h1>No files supplied</h1>", 400

    for f in files:
        filename = secure_filename(f.filename)
        filename = cfg.CLOUD_PATH / folder / filename
        f.save(filename.as_posix())

    log(
        "User %r upload files to folder %r: %s",
        get_user(),
        folder,
        [secure_filename(x.filename) for x in request.files.getlist("files")],
    )
    return redirect("/")


@app.route("/hide/<path:filepath>", methods=["GET"])
def hide(filepath):
    add_to_hides(filepath)
    return "done", 200


@app.route("/unhide/<path:filepath>", methods=["GET"])
def unhide(filepath):
    remove_from_hides(filepath)
    return "done", 200


@app.route("/unhide-all", methods=["GET"])
def unhide_all():
    for folder in get_hides():
        remove_from_hides(folder)
    return "done", 200


@app.route("/d/<path:filepath>", methods=["GET"])
@app.route("/delete/<path:filepath>", methods=["GET"])
def delete(filepath):
    filepath = cfg.CLOUD_PATH / filepath

    try:
        if filepath.is_dir():
            shutil.rmtree(filepath)
            log("User %r removed tree %r", get_user(), filepath.as_posix())
            return f"{META}<h1>Tree removed</h1> {filepath.as_posix()}", 200
        else:
            os.remove(filepath)
            log("User %r removed file %r", get_user(), filepath.as_posix())
            return f"{META}<h1>File deleted</h1>  {filepath.as_posix()}", 200
    except FileNotFoundError:
        log("User %r tried to incorrectly remove %r", get_user(), filepath.as_posix())
        return f"{META2}<h1>File not found</h1> {filepath.as_posix()}", 404


@app.route("/md/<path:folder>", methods=["GET"])
@app.route("/mk/<path:folder>", methods=["GET"])
@app.route("/mkdir/<path:folder>", methods=["GET"])
def mkdir(folder: str):
    os.makedirs(cfg.CLOUD_PATH / folder)

    log("User %r made dir %r", get_user(), folder)
    return redirect("/files")


@app.route("/mv", methods=["GET"])
@app.route("/move", methods=["GET"])
def move():
    _from = request.args.get("from")
    _to = request.args.get("to")

    if not _from:
        log('User %r tried to move, but forgot "from" argument', get_user())
        return '<h1>Missing "from" argument</h1>', 400

    if not _to:
        log('User %r tried to move, but forgot "to" argument', get_user())
        return '<h1>Missing "to" argument</h1>', 400

    real_from = cfg.CLOUD_PATH / _from
    real_to = cfg.CLOUD_PATH / _to

    try:
        shutil.move(real_from, real_to)
        log("User %r moved file %r to %r", get_user(), _from, _to)
        return f"{META}<h1>File moved correctly</h1>", 200
    except FileNotFoundError as err:
        log(
            "User %r tried to move file %r to %r, but failed (%r)",
            get_user(),
            _from,
            _to,
            err,
        )
        return f"{META2} File not found", 400
