from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import uuid

app = Flask(__name__)
app.secret_key = 'IGRUS_CC_STUDY'

# 기본 설정을 제거
DEFAULT_DYNAMODB_TABLE = None
DEFAULT_S3_BUCKET = None
dynamodb_table = os.getenv('DYNAMODB_TABLE', DEFAULT_DYNAMODB_TABLE)
s3_bucket = os.getenv('S3_BUCKET', DEFAULT_S3_BUCKET)

# AWS 클라이언트 설정
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
s3 = boto3.client('s3')

# 홈 페이지
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/members')
def members():
    if not dynamodb_table:
        flash('DynamoDB table is not configured. Please set it in the settings.', 'error')
        return redirect(url_for('settings'))
    
    try:
        table = dynamodb.Table(dynamodb_table)
        response = table.scan()
        members_list = response.get('Items', [])
        return render_template('members.html', members=members_list)
    except ClientError as e:
        flash(f'Error accessing DynamoDB: {e}', 'error')
        return render_template('members.html', members=[])

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        if not dynamodb_table or not s3_bucket:
            flash('DynamoDB table or S3 bucket is not configured. Please set them in the settings.', 'error')
            return redirect(url_for('settings'))

        name = request.form['name']
        student_id = request.form['student_id']
        department = request.form['department']
        photo = request.files['photo']

        # S3에 사진 업로드
        if photo and s3_bucket:
            photo_filename = f"{uuid.uuid4()}-{photo.filename}"
            try:
                s3.upload_fileobj(photo, s3_bucket, photo_filename)
                photo_url = f"https://{s3_bucket}.s3.amazonaws.com/{photo_filename}"
            except ClientError as e:
                flash(f'Error uploading to S3: {e}', 'error')
                return redirect(url_for('add_member'))
        else:
            photo_url = ''
        
        # DynamoDB에 회원 정보 저장
        try:
            table = dynamodb.Table(dynamodb_table)
            table.put_item(
                Item={
                    'name': name,
                    'student_id': student_id,
                    'department': department,
                    'photo_url': photo_url
                }
            )
        except ClientError as e:
            flash(f'Error saving to DynamoDB: {e}', 'error')
            return redirect(url_for('add_member'))

        return redirect(url_for('members'))
    return render_template('add_member.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global dynamodb_table, s3_bucket
    if request.method == 'POST':
        dynamodb_table = request.form.get('dynamodb_table', DEFAULT_DYNAMODB_TABLE)
        s3_bucket = request.form.get('s3_bucket', DEFAULT_S3_BUCKET)
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('home'))
    return render_template('settings.html', dynamodb_table=dynamodb_table or 'Not set', s3_bucket=s3_bucket or 'Not set')

if __name__ == '__main__':
    app.run(debug=True)
