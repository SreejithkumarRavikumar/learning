import requests
import sys
import json
import math
import xml.etree.ElementTree
import re

# Defining Needed Dictionaries
metricsDictionary = {}
queueDictionary = {}
sparkConf = {}
executorConf = {}

def getActiveNameNode():
        rpcNameList = getNameNodeInfo(sys.argv[1])
        url = "http://"+rpcNameList[0]+":8088/ws/v1/cluster/"
        resp = requests.get(url + "info")
        obj = json.loads(resp.content)
        #print(json.dumps(obj, indent=2, sort_keys=True))
        if obj["clusterInfo"]["haState"] == "ACTIVE":
                return url
        else:
                url = "http://"+rpcNameList[1]+":8088/ws/v1/cluster/"
                return url

def getclusterMetrics(serverName):
        url = serverName + "metrics"
        resp = requests.get(url)
        obj = json.loads(resp.content)
        #print(json.dumps(obj, indent=2, sort_keys=True))
        metricsDictionary["activeNodes"] = obj["clusterMetrics"]["activeNodes"]
        metricsDictionary["availableMB"] = obj["clusterMetrics"]["availableMB"]
        metricsDictionary["availableVirtualCores"] = obj["clusterMetrics"]["availableVirtualCores"]
        metricsDictionary["totalMB"] = obj["clusterMetrics"]["totalMB"]


def getQueueMetrics(serverName, activeQueue):
        url = serverName + "scheduler"
        resp = requests.get(url)
        obj = json.loads(resp.content)
        availableQueus = len(obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"])
        #print("Configured Queues in Cluster: " + str(availableQueus))
        for i in range(availableQueus):
                if obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"][i]["queueName"] == activeQueue:
                        #print(json.dumps(obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"][i], indent=2, sort_keys=True))

                        # To Derive absolute capacity from the queue metrics:
                        abCap = obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"][i]["absoluteCapacity"]
                        abCap = int((metricsDictionary["totalMB"] / 100) * abCap)
                        queueDictionary["absoluteCapacity"] = abCap

                        # To derive absolute Max capacity of the queue
                        abMaxCap = obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"][i]["absoluteMaxCapacity"]
                        abMaxCap = int((metricsDictionary["totalMB"] / 100) * abMaxCap)
                        queueDictionary["absoluteMaxCapacity"] = abMaxCap

                        # To derive absolute used capacity of the queue
                        abUsedCap = obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"][i]["absoluteUsedCapacity"]
                        abUsedCap = int((metricsDictionary["totalMB"] / 100) * abUsedCap)
                        queueDictionary["absoluteUsedCapacity"] = abUsedCap

                        queueDictionary["numActiveApplications"] = obj[u"scheduler"][u"schedulerInfo"][u"queues"][u"queue"][i]["numActiveApplications"]

def getSparkConf():
        totalCores = metricsDictionary["availableVirtualCores"]
        #print("Total Cores: "+ str(totalCores))
        sparkConf["totalCores"]= totalCores

        totalExecutors = int(totalCores/5)
        #print("Total Executors: "+ str(totalExecutors))
        sparkConf["totalExecutors"] = totalExecutors

        #executorMemory = int(metricsDictionary["availableMB"] / totalExecutors / 1024)
        executorMemory = int(metricsDictionary["totalMB"] / totalExecutors / 1024)
        #print("Executor Memory: "+ str(executorMemory))
        sparkConf["executorMemory"] = executorMemory

def getFinalconf(dataSize):
        defaultReservedMemory = sparkConf["executorMemory"] * 90/100
        defaultCacheMemory = defaultReservedMemory * 60/100
        executorMemory = math.floor(defaultCacheMemory)
        executorCores = 0
        for i in range(1,sparkConf["totalExecutors"]):
                if (i * executorMemory <= int(dataSize)):
                        executorCores = i + 1
        executorConf["numExecutors"]= executorCores
        executorConf["executorCores"] = 4


def getNameNodeInfo(siteXml):
        nodeName = []
        hdfsSiteXml = xml.etree.ElementTree.parse(siteXml).getroot()
        for elem in hdfsSiteXml.findall('property'):
                hname = elem.find('./name').text
                if (hname.startswith("dfs.namenode.http-address.")):
                        hval = elem.find("./value").text
                        nodeName.append(hval.split(':')[0])
        return nodeName



serverName = getActiveNameNode()
getclusterMetrics(serverName)
#print ("Cluster Metrics: "+ str(metricsDictionary))

#getQueueMetrics(serverName, "sgz1-hismigapp-haas_prd")
getQueueMetrics(serverName, sys.argv[2])
#print("Queue Metrics: "+str(queueDictionary))
getSparkConf()
#print("Spark Conf: " + str(sparkConf))

getFinalconf(sys.argv[3])
#print("Executor Configuration: " + str(executorConf))
if (executorConf["numExecutors"] != 0 & sparkConf["executorMemory"] != 0):
        print(str(executorConf["numExecutors"]) +":" +str(executorConf["executorCores"]) +":"+ str(sparkConf["executorMemory"]))
else:
        print("No Executors available on the Queue, wait for sometime...!")
