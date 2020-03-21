import random
import string
#import gzip
import datetime
import urllib
import traceback
import boto3
from boto3.dynamodb.conditions import Key
from chalice import Chalice, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

TABLE_NAME='keijiban'

app = Chalice(app_name='keijiban')
#dynamoclient = boto3.client('dynamodb')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

jinja2env = Environment(loader=FileSystemLoader('./chalicelib/templates/'),
                        autoescape=select_autoescape(['html','htm','xml']))
top_tmpl = jinja2env.get_template('top.html')
detail_tmpl = jinja2env.get_template('detail.html')
e500_tmpl = jinja2env.get_template('e500.html')

threadlistItems = {}
threadDetails = {}

@app.route('/', methods=['GET'])
def threadlist_show():
    try:
        varss = make_varss_4_threadlist()
        result = top_tmpl.render(varss)
        return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
        varss = {}
        result = e500_tmpl.render(varss)
        return Response(body=result,status_code=500,headers={'Content-Type': 'text/html'})

@app.route('/', methods=['POST'],content_types=['application/x-www-form-urlencoded'])
def threadlist_post():
    title = ""
    varss = {}
    try:
        postReq = app.current_request.raw_body.decode()
        req_param = urllib.parse.parse_qs(postReq)
        csrf_token = req_param['csrf'][0] 
        title = req_param['title'][0]
        varss = make_varss_4_threadlist()
        if checkCSRF(varss['ipaddr'],csrf_token)==False:
            varss['message'] = "もう一度お試しください。"
            varss['input_title'] = title
            result = top_tmpl.render(varss)
            return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})
        threads = create_thread(title)
        varss['threads'] = threads
        result = top_tmpl.render(varss)
        return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
        result = top_tmpl.render(varss)
        return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})

@app.route('/{num}', methods=['GET'])
def threaddetail_show(num):
    try:
        varss = make_varss_4_threaddetail(num)
        result = detail_tmpl.render(varss)
        return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
        varss = {}
        result = e500_tmpl.render(varss)
        return Response(body=result,status_code=500,headers={'Content-Type': 'text/html'})

@app.route('/{num}', methods=['POST'],content_types=['application/x-www-form-urlencoded'])
def threaddetail_post(num):
    title = ""
    varss = {}
    try:
        postReq = app.current_request.raw_body.decode()
        req_param = urllib.parse.parse_qs(postReq)
        csrf_token = req_param['csrf'][0] 
        comment = req_param['comment'][0]
        writer = req_param['name'][0]
        varss = make_varss_4_threaddetail(num)
        if checkCSRF(varss['ipaddr'],csrf_token)==False:
            varss['message'] = "もう一度お試しください。"
            varss['input_comment'] = comment
            varss['input_name'] = writer
            result = detail_tmpl.render(varss)
            return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})
        details = create_message(num,comment,writer,varss['ipaddr'])
        varss['details'] = details
        result = detail_tmpl.render(varss)
        return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
        result = detail_tmpl.render(varss)
        return Response(body=result,status_code=200,headers={'Content-Type': 'text/html'})

def make_varss_4_threadlist():
    csrf_token = makeCSRF(app.current_request.context['identity']['sourceIp'])
    threads = get_or_cache_threadlist()
    varss = {'csrf_token':csrf_token['range'],'threads':threads,'ipaddr':app.current_request.context['identity']['sourceIp']}
    return varss

def make_varss_4_threaddetail(num):
    csrf_token = makeCSRF(app.current_request.context['identity']['sourceIp'])
    threads = get_or_cache_threadlist()
    title = ""
    for item in threads:
        if item['range']==num:
            if item['disabled']==True:
                raise Exception("disabled")
            title = item['title']
            break
    details = get_or_cache_threadDetail(num)
    varss = {'csrf_token':csrf_token['range'],'title':title,'details':details,'ipaddr':app.current_request.context['identity']['sourceIp']}
    return varss

def makeCSRF(ipaddr,n=128):
    csrf_token = ''.join(random.choices(string.ascii_letters + string.digits, k=n))
    expired = datetime.datetime.now()+ datetime.timedelta(minutes=30)
    expired_str = expired.strftime('%Y-%m-%d %H:%M:%S')
    expired_unix = expired.strftime('%s')
    item_dict={'hash':'csrf','range':csrf_token,'expired':expired_str,'ip':ipaddr,'ttl':expired_unix}
    table.put_item(Item=item_dict)
    return item_dict

def checkCSRF(ipaddr,csrf_token):
    try:
       item_dict = {'hash':'csrf','range':csrf_token}
       target = table.get_item(Key=item_dict)
       item_dict = target["Item"]
       if item_dict['ip'] != ipaddr:
           return False
       expired = datetime.datetime.strptime(item_dict['expired'], '%Y-%m-%d %H:%M:%S')
       if expired < datetime.datetime.now():
           return False
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
        return False
    try:
       item_dict = {'hash':'csrf','range':csrf_token}
       table.delete_item(Key=item_dict)
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
    return True

def get_or_cache_threadlist():
    global threadlistItems
    if threadlistItems == {}:
        threadlistItems['list']=get_threadlist()
        threadlistItems['date']=datetime.datetime.now()
    elif  threadlistItems['date'] < datetime.datetime.now() - datetime.timedelta(minutes=5):
        threadlistItems['list']=get_threadlist()
        threadlistItems['date']=datetime.datetime.now()
    return threadlistItems['list']

def get_threadlist():
    response = table.query(KeyConditionExpression=Key('hash').eq('threadlist'),ScanIndexForward=False)
    result = response['Items']
    try:
        while 'LastEvaluatedKey' in response:
            response = table.query(KeyConditionExpression=Key('hash').eq('threadlist'),ScanIndexForward=False,
                                   ExclusiveStartKey=response['LastEvaluatedKey'])
            result += response['Items']
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
    return result

def create_thread(title):
    get_or_cache_threadlist()
    threadIndex = get_threadindex()
    create_date = datetime.datetime.now()
    create_date_str = create_date.strftime('%Y-%m-%d %H:%M:%S')
    item_dict={'hash':'threadlist','range':str(threadIndex),'title':title,'date':create_date_str,'disabled':False}
    table.put_item(Item=item_dict)
    global threadlistItems
    threadlistItems['list'].insert(0,item_dict)
    threadlistItems['date']=datetime.datetime.now()
    return threadlistItems['list']    
    
def get_threadindex():
    response = table.update_item(Key={'hash':'index','range':'thread'},ReturnValues='ALL_NEW',
                                 UpdateExpression='ADD indexs :incr',ExpressionAttributeValues={':incr': 1} )
    return response['Attributes']['indexs']

def get_or_cache_threadDetail(num):
    global threadDetails
    if num not in threadDetails:
        threadDetails[num]={}
        threadDetails[num]['list']=get_threadDetail(num)
        threadDetails[num]['date']=datetime.datetime.now()
    elif  threadDetails[num]['date'] < datetime.datetime.now() - datetime.timedelta(minutes=5):
        threadDetails[num]['list']=get_threadDetail(num)
        threadDetails[num]['date']=datetime.datetime.now()
    return threadDetails[num]['list']

def get_threadDetail(num):
    response = table.query(KeyConditionExpression=Key('hash').eq('thread_'+num),ScanIndexForward=False)
    result = response['Items']
    try:
        while 'LastEvaluatedKey' in response:
            response = table.query(KeyConditionExpression=Key('hash').eq('thread_'+num),ScanIndexForward=False,
                                   ExclusiveStartKey=response['LastEvaluatedKey'])
            result += response['Items']
    except Exception as e:
        app.log.error('ERROR:'+str(e))
        app.log.error(traceback.format_exc())
    return result

def create_message(num,body,writer,ipaddr):
    get_or_cache_threadDetail(num)
    ind = get_threadDetailIndex(num)
    create_date = datetime.datetime.now()
    create_date_str = create_date.strftime('%Y-%m-%d %H:%M:%S')
    item_dict={'hash':'thread_'+num,'range':str(ind),'body':body,'writer':writer,'ipaddr':ipaddr,'date':create_date_str,'disabled':False}
    table.put_item(Item=item_dict)
    global threadDetails
    threadDetails[num]['list'].insert(0,item_dict)
    threadDetails[num]['date']=datetime.datetime.now()
    return threadDetails[num]['list']
    
def get_threadDetailIndex(num):
    response = table.update_item(Key={'hash':'index','range':'thread_'+num},ReturnValues='ALL_NEW',
                                 UpdateExpression='ADD indexs :incr',ExpressionAttributeValues={':incr': 1} )
    return response['Attributes']['indexs']

