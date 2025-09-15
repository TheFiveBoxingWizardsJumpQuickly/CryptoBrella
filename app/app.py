import os
import app.gear as gear
import app.secret.cryptobrella as cryptobrella

from app.prosaic import prose
from flask import Flask, render_template, request, send_from_directory, url_for, jsonify
from app.line_bot_blueprint import bp as line_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(line_bp)
    return app

app = create_app()
app.config['IMAGE_UPLOAD_FOLDER'] = os.path.join(
    app.root_path, 'temporary', 'upload')
app.config['IMAGE_RESULT_FOLDER'] = os.path.join(
    app.root_path, 'temporary', 'result')
app.config['SECRET_IMAGE_FOLDER'] = os.path.join(
    app.root_path, 'secret', 'img')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html', BASEURL=request.url_root,)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/image'), 'favicon.ico', )


@app.route('/<string:file>')
def show_page(file):
    file = file.split('.')[0]
    return render_template('Tools/'+file+'.html', BASEURL=request.url_root)


@app.route('/passcode/')
@app.route('/passcode/<int:id>')
def passcode_index(id=None, mode=''):
    if id == None:
        mode = 'today'
        id = gear.passcode_get_today_id()
    passcode = gear.passcode_gen(id)
    return render_template('Passcode/index.html',
                           id=passcode['id'],
                           code=passcode['code'],
                           date=passcode['date'],
                           format=passcode['format'],
                           tag=passcode['tag'],
                           hint=passcode['hint'],
                           hint2=passcode['hint2'],
                           BASEURL=request.url_root,
                           mode=mode,
                           )


@app.route('/passcode/random')
def passcode_random():
    id = gear.passcode_get_random_id()
    return passcode_index(id=id, mode='random')


@app.route('/passcode/list')
def passcode_list():
    return render_template('Passcode/index.html',
                           id=1,
                           BASEURL=request.url_root,
                           mode='list',
                           )


@app.route('/passcode/howtoplay')
def passcode_howtoplay():
    return passcode_index(id=1, mode='howtoplay')


@app.route('/passcode/howtoplay_ja')
def passcode_howtoplay_ja():
    return passcode_index(id=1, mode='howtoplay_ja')


@app.route('/passcode/changelog')
def passcode_changelog():
    return render_template('Passcode/changelog.html',
                           BASEURL=request.url_root,
                           )


@app.route('/challenge/')
def challenge_index():
    return render_template('Challenge/index.html')


@app.route('/challenge/<string:pageid>')
def show_challenge_page(pageid):
    existing_challenge_page_ids = cryptobrella.cb_challenge_contents(
        mode='keys', pageid=None)
    existing_page_ids = cryptobrella.cb_contents(
        mode='keys', pageid=None)
    if pageid in existing_challenge_page_ids:
        content = cryptobrella.cb_challenge_contents(
            mode='page', pageid=pageid)
        return render_template('Challenge/challenge.html.jinja',
                               BASEURL=request.base_url,
                               title=content['title'],
                               puzzle=content['puzzle'],
                               answer_hash=content['answer_hash'],
                               hint=content['hint'],
                               )
    elif pageid in existing_page_ids:
        content = cryptobrella.cb_contents(
            mode='page', pageid=pageid)
        return render_template('Challenge/challenge_no_form.html.jinja',
                               BASEURL=request.base_url,
                               title=content['title'],
                               content=content['content'],
                               )
    else:
        return render_template('Challenge/cb_404.html')


@app.route('/prosaic/<string:pageid>')
def show_prosaic_page(pageid):
    existing_page_ids = prose(
        mode='keys', pageid=None)
    if pageid in existing_page_ids:
        content = prose(
            mode='page', pageid=pageid)
        return render_template('prosaic.html.jinja',
                               BASEURL=request.base_url,
                               title=content['title'],
                               lang=content['lang'],
                               about=content['about'],
                               how_to_use_tool=content['how_to_use_tool'],
                               test_cases=content['test_cases'],
                               challenge=content['challenge'],
                               link=content['link'],
                               )
    else:
        return '404'


@app.route('/gear/<string:function>', methods=['post'])
def cipher_gear(function):
    return gear.gear_globals()[function](request)


@app.route('/g/resize/', methods=['POST'])
def resize():
    image = request.files['image']
    img_width = request.form['img_width']
    img_height = request.form['img_height']
    bgcolor = request.form['bgcolor']
    output_name = request.form['output_name']

    image.save(os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], image.filename))
    final_output_name = gear.resize_image(input_dir=app.config['IMAGE_UPLOAD_FOLDER'],
                                          output_dir=app.config['IMAGE_RESULT_FOLDER'],
                                          filename=image.filename,
                                          canvas_w=img_width,
                                          canvas_h=img_height,
                                          bgcolor_prop=bgcolor,
                                          output_name=output_name)
    image_url = url_for('get_image_result', filename=final_output_name)
    return jsonify({'image_url': image_url})


@ app.route('/upload/', methods=['GET'])
def get_image_upload():
    filename = request.args.get('filename')
    return send_from_directory(app.config['IMAGE_UPLOAD_FOLDER'], filename)


@ app.route('/modified_image/')
def get_image_result():
    filename = request.args.get('filename')
    return send_from_directory(app.config['IMAGE_RESULT_FOLDER'], filename)


@ app.route('/secret/img/<string:filename>')
def get_secret_image(filename):
    return send_from_directory(app.config['SECRET_IMAGE_FOLDER'], filename)
