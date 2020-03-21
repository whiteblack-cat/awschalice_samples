import app
#from http import HTTPStatus
#import boto3

def test_001_csrf():
    csrf = app.makeCSRF('127.0.0.1')
    assert app.checkCSRF('127.0.0.1',csrf['range']) == True
    assert app.checkCSRF('127.0.0.1',csrf['range']) == False
    csrf = app.makeCSRF('127.0.0.1')
    assert app.checkCSRF('127.0.0.2',csrf['range']) == False

def test_002_threadlist():
    threads = app.get_threadlist()
    assert threads == []
    app.create_thread("title 1")
    threads = app.get_threadlist()
    assert threads[0]['title'] == "title 1"
    assert threads[0]['range'] == "1"

def test_003_threadDetail():
    app.create_thread("title 1")
    details = app.get_threadDetail("1")
    assert details == []
    app.create_message(num="1",body="message body",writer="writer",ipaddr="127.0.0.1")
    details = app.get_threadDetail("1")
    assert details[0]["body"] == "message body"

#def test_index(client):
#    response = client.get('/')
#    assert response.status_code == HTTPStatus.OK
#    assert response.json == {'hello': 'world'}
