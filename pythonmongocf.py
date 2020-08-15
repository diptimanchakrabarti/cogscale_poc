import pymongo
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify
import atexit
import os
import json
import ssl
import uuid
from random import seed
from random import random, randint

app = Flask(__name__)

db_name = 'guestbook'
client = None
db = None

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    print(vcap)
    if 'databases-for-mongodb' in vcap:
        conndtls = vcap['databases-for-mongodb'][0]['credentials']['connection']['mongodb']
        sslcd=conndtls['certificate']['certificate_base64']
        creds=conndtls['authentication']
        user = creds['username']
        password = creds['password']
        connPaths=conndtls['hosts']
        #url = 'https://' + creds['host']
        #client = Cloudant(user, password, url=url, connect=True)
        #db = client[db_name] 
elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        conndtls = vcap['connection']['mongodb']
        sslcd=conndtls['certificate']['certificate_base64']
        creds=conndtls['authentication']
        user = creds['username']
        password = creds['password']
        connPaths=conndtls['hosts']
else:
    with open('./vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        conndtls = vcap['connection']['mongodb']
        sslcd=conndtls['certificate']['certificate_base64']
        creds=conndtls['authentication']
        user = creds['username']
        password = creds['password']
        connPaths=conndtls['hosts']
connectionString = "mongodb://"+user+":"+password+"@"+connPaths[0]['hostname']+":"+str(connPaths[0]['port'])+","+connPaths[0]['hostname']+":"+str(connPaths[0]['port'])+"/?replicaSet=replset"
print(connectionString)
print(sslcd)
mongoDBName="JEDIMVP1"
client = MongoClient(connectionString,ssl=True,ssl_cert_reqs=ssl.CERT_NONE) 
#client = MongoClient(connectionString,ssl=True,ssl_ca_certs=sslcd) 
dbNm=client[mongoDBName]
collectionLst=dbNm.list_collection_names()
print(collectionLst)
port = int(os.getenv('PORT', 8000))

def calcPay(provamt,maxddct,maxoop,amaxddct,amaxoop):
    provamt=int(provamt)
    if maxddct>amaxddct:
        if provamt>(maxddct-amaxddct):
            ddctble=maxddct-amaxddct
            dueamt=provamt-ddctble
            inspay=(dueamt*80)/100
            coins=dueamt-inspay
            userpay=coins+ddctble
            provpay=provamt-userpay
        else:
            userpay=provamt
            inspay=0
            ddctble=userpay
            coins=0
    else:
        ddctble=0
        inspay=(provamt*80)/100
        coins=provamt-inspay
        userpay=coins

    return ddctble,inspay,coins,userpay

def parseRcrdset(rcrdset, *args):
    print(len(args))
    newrcrdset=[]
    retrecord=[]
    
    if args[0]=="P":
        dbNm[args[8]].drop()
        mytab=dbNm[args[8]]
        modrcrd=rcrdset
        print("got record")
        for record in modrcrd:
            ddctble,inspay,coins,userpay=calcPay(record['Charged_Amt'],args[1],args[2],args[3],args[4])
            #record1=record
            #retrecord.append(record1)
            #record1['totalCost']=record1['Charged_Amt']
            #record1['patLiablty']=userpay
            record['copay']=0
            record['payerLiability']=inspay
            record['coinsurance']=coins
            record['deductable']=ddctble
            record['patLiablty']=userpay
            record['totalCost']=record['Charged_Amt']
            record.pop('Charged_Amt')
            record.pop('diagCode')
            record.pop('procedureCode')
            record.pop('ratingsCount')
            #record1.pop('Charged_Amt')
            record['memberId']=args[5]
            record['diagCode']=args[6]
            record['procedureCode']=args[7]
            newrcrdset.append(record)
            
        try:
            mytab.insert_many(newrcrdset)
            #print(retrecord)
            retval=list(mytab.find({},{"providerId":1,"providerName":1,"providerAddress":1,"zipcode":1,"diagCode":1,"procedureCode":1,"patLiablty":1,"providerAddress":1,"city":1,"state":1,"providerContact":1,"nextAvailbility":1,"url":1,'_id': False}))
            return retval
        except:
            print("exception Occurred and Handled")
            return {"status":400,"description":"Data Fetching failed"}
            #print(userpay)
    elif args[0]=="PD":
        mytab=dbNm[args[3]]
        retval=list(mytab.find({"providerId":args[2],"memberId":args[1]},{'_id': False}))
        print(retval)
        return retval
    elif args[0]=="AS":
        mytab=dbNm[args[1]]
        mytab.insert_one(rcrdset)
        return "0"
    elif args[0]=="PAT":
        mytab=dbNm[args[9]]
        retval=list(mytab.find({"uniqueappointmentKey":args[8]},{args[1]:1,args[2]:1,args[3]:1,args[4]:1,args[5]:1,args[6]:1,args[7]:1,'_id': False}))
        return retval

@app.route('/')
def get_response():
    print("got values")
    return jsonify({"satus":200})

@app.route('/api')
def get_newresponse():
    print("got values")
    return jsonify({"satus":200})



@app.route('/api/getProv', methods=['POST'])
def get_provider():
    print("again got values")
    mbrid=request.json['memberId']
    diagcd=request.json['diagCode']
    proccd=request.json['procedureCode']
    zipcode=request.json['zipcode']
    collectionName="provider_info"
    srchClctnName="member_info"
    tempStore="encounter_init_process"
    recordset=list(dbNm[collectionName].find({},{'_id': False}))
    mbrinfo=list(dbNm[srchClctnName].find({"member_id":mbrid},{'_id': False}))
    #print(mbrinfo)
    maxddct=mbrinfo[0]['dedcutable_max']
    maxoop=mbrinfo[0]['oop_max']
    amaxddct=mbrinfo[0]['accumulated_oop_max']
    amaxoop=mbrinfo[0]['accumulated_deductable_max']
    prov_dict={}
    #recordset1=dict(recordset)
    #print(recordset1)
    modrecordset=recordset
    #prov_dict['providers']=modrecordset
    #selector1={"email":{"$eq":res}}
    #results1=db.get_query_result(selector1)
    if recordset:
        #targetresult=list(recordset)
        #print(targetresult)
        #return jsonify({"status":200})
        retval=parseRcrdset(recordset, "P",maxddct,maxoop,amaxddct,amaxoop,mbrid,diagcd,proccd,tempStore)
        print(retval)
        prov_dict['providers']=retval
        prov_dict['status']=200
        return jsonify(prov_dict)
        #return jsonify([{"status":200}])
    else:
        print('No value returned')
        return jsonify({"status":400,"Description":"Data Not Found"})

@app.route('/api/getProvDtls', methods=['POST'])
def get_prov_dtls():
    
    mbrid=request.json['memberId']
    diagcd=request.json['diagCode']
    proccd=request.json['procedureCode']
    #zipcode=request.json['zipcode']
    provid=request.json['providerId']
    tempStore="encounter_init_process"
    provdtls=parseRcrdset("NA", "PD",mbrid,provid,tempStore)
    if provdtls:
        prov_dtls=provdtls[0]
        prov_dtls['status']=200
        return prov_dtls
    else:
        return jsonify({"status":400,"Description":"Data not Found"})
    
@app.route('/api/saveAppointments', methods=['POST'])
def put_appointment():
    
    memberId=request.json['memberId']
    diagCode=request.json['diagCode']
    procedureCode=request.json['procedureCode']
    #zipcode=request.json['zipcode']
    providerid=request.json['providerId']
    providerName=request.json['providerName']
    totalCost=request.json['totalCost']
    copay=request.json['copay']
    payerLiability=request.json['payerLiability']
    coinsurance=request.json['coinsurance']
    deductable=request.json['deductable']
    patLiablty=request.json['patLiablty']
    appointmentDate=request.json['appointmentDate']
    appointmentTime=request.json['appointmentTime']
    ampm=request.json['ampm']
    uniqueappointmentKey=str(uuid.uuid4().hex)
    preAuthRqrd='Y'
    seed(1)
    PreAuthID='AF'+str(randint(100000,999999))
    PreAuthStatus='In Progress'
    rcrdset={"memberId":memberId,"diagCode":diagCode,"procedureCode":procedureCode,"providerid":providerid,"providerName":providerName,"patLiablty":patLiablty,"appointmentDate":appointmentDate,"appointmentTime":appointmentTime,"ampm":ampm,"uniqueappointmentKey":uniqueappointmentKey,"preAuthRqrd":preAuthRqrd,"PreAuthID":PreAuthID,"PreAuthStatus":"Approved and Closed","QrStatus":"A"}

    tempStore="appointment_schedule"
    apnmntSchdl=parseRcrdset(rcrdset, "AS",tempStore)
    print(apnmntSchdl)
    if apnmntSchdl:
        if apnmntSchdl=="0":
           return jsonify({"status":200,"memberId":memberId,"diagCode":diagCode,"procedureCode":procedureCode,"providerid":providerid,"providerName":providerName,"patLiablty":patLiablty,"appointmentDate":appointmentDate,"appointmentTime":appointmentTime,"ampm":ampm,"uniqueappointmentKey":uniqueappointmentKey,"preAuthRqrd":preAuthRqrd,"PreAuthID":PreAuthID,"PreAuthStatus":PreAuthStatus,"QrStatus":"A"})
        else:
           return jsonify({"status":400,"Description":"Data not Found"})
    else:
        return jsonify({"status":400,"Description":"Data not Found"})
    

@app.route('/api/rfrshPreAuth', methods=['POST'])
def get_preauth():
    uniqueappointmentKey=request.json['uniqueappointmentKey']
    tempStore="appointment_schedule"
    retval=parseRcrdset("NA", "PAT","uniqueappointmentKey","providerName","patLiablty","appointmentDate","appointmentTime","ampm","PreAuthStatus",uniqueappointmentKey,tempStore)
    if retval:
        retval[0]['status']=200
        return jsonify(retval[0])
    else:
        return jsonify({"status":400,"Description":"Data not Found"})

@app.route('/api/expireQR', methods=['POST'])
def get_QRexpire():
    uniqueappointmentKey=request.json['uniqueappointmentKey']
    tempStore="appointment_schedule"
    retval=parseRcrdset("NA", "PAT","uniqueappointmentKey","providerName","patLiablty","appointmentDate","appointmentTime","ampm","PreAuthStatus",uniqueappointmentKey,tempStore)
    if retval:
        retval[0]['QrStatus']="E"
        retval[0]['status']=200
        return jsonify(retval[0])
    else:
        return jsonify({"status":400,"Description":"Data not Found"})
@atexit.register
def shutdown():
    if client:
        client.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)