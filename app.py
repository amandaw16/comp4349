# import libs

from flask import Flask, request, render_template, redirect, url_for
import boto3
import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# config
S3_BUCKET = 'awal8482-img-bucket'
THUMBNAIL_PREFIX = 'thumbnails/'

DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

# s3 client 
s3 = boto3.client('s3')

# DB connection helper
def get_db():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def home():
    return redirect(url_for('upload'))


@app.route('/health')
def health_check():
    return 'OK', 200


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['image']
        filename = file.filename
        timestamp = datetime.utcnow()

        # Define S3 key (in 'uploads/' folder)
        s3_key = f"uploads/{filename}"

        # Upload to S3
        s3.upload_fileobj(file, S3_BUCKET, s3_key)

        # Insert metadata into RDS
        conn = get_db()
        with conn:
            with conn.cursor() as cursor:
                sql = "INSERT INTO captions (image_key, caption, thumbnail_url, uploaded_at) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (s3_key, None, None, timestamp))
            conn.commit()

        return redirect(url_for('gallery'))

    return render_template('upload.html')


@app.route('/gallery')
def gallery():
    conn = get_db()
    images = []
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM captions")
            images = cursor.fetchall()

    for img in images:
        img['s3_url'] = f"https://{S3_BUCKET}.s3.amazonaws.com/{img['image_key']}"
       	filename = img['image_key'].split('/')[-1]
        img['thumbnail_url'] = f"https://{S3_BUCKET}.s3.amazonaws.com/thumbnails/{filename}"
    return render_template('gallery.html', images=images)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
