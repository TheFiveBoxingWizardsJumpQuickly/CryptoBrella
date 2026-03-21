import os
import random
import app.gear as gear
import app.secret.cryptobrella as cryptobrella

from app.cipher_docs import get_cipher_doc_page
from app.link_catalog import get_link_sections
from app.tool_catalog import get_home_catalog
from flask import Flask, abort, render_template, request, send_from_directory, url_for, jsonify


NOT_FOUND_MESSAGES = [
    "A simple umbrella, a simple cipher, a little peace of mind.",
    "An umbrella is comfort in rain or code.",
    "A CryptoBrella is a shelter you carry with you.",
    "Both ciphers and umbrellas protect, but they also hide the sky.",
    "Better an umbrella in sunshine than none in a cipher storm.",
    "Ciphers and umbrellas are the simplest forms of preparedness.",
    "A good umbrella is quiet insurance. So is a good cipher.",
    "An umbrella protects against storms. CryptoBrella protects against mystery.",
    "An umbrella makes its own small world. A cipher makes its own small secret.",
    "Many ciphers, one umbrella.",
]

def create_app():
    return Flask(__name__)

app = create_app()
app.config['IMAGE_UPLOAD_FOLDER'] = os.path.join(
    app.root_path, 'temporary', 'upload')
app.config['IMAGE_RESULT_FOLDER'] = os.path.join(
    app.root_path, 'temporary', 'result')
app.config['SECRET_IMAGE_FOLDER'] = os.path.join(
    app.root_path, 'secret', 'img')


@app.route('/')
def index():
    return render_template('index.html', catalog_sections=get_home_catalog())


@app.route('/about')
def about():
    return render_template('about.html', BASEURL=request.url_root,)


@app.route('/link')
def link():
    return render_template('Tools/link.html', BASEURL=request.url_root, link_sections=get_link_sections())


@app.errorhandler(404)
def page_not_found(error):
    initial_index = random.randrange(len(NOT_FOUND_MESSAGES))
    return render_template(
        '404.html',
        BASEURL=request.url_root,
        not_found_messages=NOT_FOUND_MESSAGES,
        initial_message_index=initial_index,
    ), 404


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/image'), 'favicon.ico', )


@app.route('/<string:file>')
def show_page(file):
    file = file.split('.')[0]
    template_path = os.path.join(app.root_path, 'templates', 'Tools', file + '.html')
    if not os.path.exists(template_path):
        abort(404)
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
        abort(404)


@app.route('/cipher_docs/<string:pageid>')
def show_cipher_doc_page(pageid):
    existing_page_ids = get_cipher_doc_page(
        mode='keys', pageid=None)
    if pageid in existing_page_ids:
        content = get_cipher_doc_page(
            mode='page', pageid=pageid)
        return render_template('cipher_docs.html.jinja',
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
        abort(404)


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
