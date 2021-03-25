import numpy as np
import requests
from datetime import date, timedelta
import pandas as pd
import datetime
import uuid

class Export:
    def __init__(self, graph):
        self.graph = graph
        
    def toGEXF(self, default):
        nodes = ''
        edges = ''

        for n, node in enumerate(self.graph):
            if default == True:
                nodes = self.setNode(nodes, node.replace('"', ''), node.replace('"', ''))
            
                for edge in self.graph[node]:
                    edges = self.setEdge(edges, uuid.uuid4(), edge.replace('"', ''), node.replace('"', ''), False)
            
            else:
                label = self.graph[node]['label']
                
                nodes = self.setNode(nodes, node, label)
                
                for edge in self.graph[node]['edges']:
                    weight = self.graph[node]['edges'][edge]['weight']
                    
                    edges = self.setEdge(edges, uuid.uuid4(), edge, node, weight)
                    
                    
        base = '<?xml version="1.0" encoding="UTF-8"?>'\
                '<gexf xmlns="http://www.gexf.net/1.3" version="1.3" xmlns:viz="http://www.gexf.net/1.3/viz" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.gexf.net/1.3 http://www.gexf.net/1.3/gexf.xsd">' \
                  '<meta lastmodifieddate="2020-12-13">' \
                    '<creator>Gephi 0.9</creator>' \
                    '<description></description>' \
                  '</meta>' \
                  '<graph defaultedgetype="undirected" mode="static">' \
                    '<attributes class="node" mode="static">' \
                      '<attribute id="modularity_class" title="Modularity Class" type="integer"></attribute>' \
                    '</attributes>' \
                    f'<nodes>{nodes}</nodes>' \
                    f'<edges>{edges}</edges>' \
                  '</graph>' \
                '</gexf>'

        print('Enter filename and hit Enter:')
        filename = input()

        print('Enter full dir to save the .gexf file or just hit Enter:')
        dir = input()
        
        f = open(dir + filename + ".gexf", "w")
        f.write(base)
        f.close()

        print('File ready at: ' + dir)

    @staticmethod    
    def setNode(nodes, id, label):
        node = f'<node id="{id}" label="{label}">' \
                '</node>'+"\n"

        return nodes + node

    @staticmethod
    def setEdge(edges, id, source, target, weight):
        if weight != False:
            edge = f'<edge id="{id}" source="{source}" target="{target}" weight="{weight}">' \
                '</edge>'+"\n"
        else:
            edge = f'<edge id="{id}" source="{source}" target="{target}">' \
                '</edge>'+"\n"
            
        return edges + edge

class Graph:   
    def __init__(self, filename):      
        csvCountryBordersFile = open(filename)
        self.countryBordersArray = np.genfromtxt(csvCountryBordersFile, delimiter=',', dtype='str')

    def generate(self):
        graph = {}
        self.graphCountries = []
        
        for r, row in enumerate(self.countryBordersArray):
            countryCode = row[0]
            countryName = row[1]
            countryNeighbourCode = row[2]
            countryNeighbourName = row[3]

            self.graphCountries.append(countryName)
            
            if r == 0:
                continue
            if countryName not in graph:
                graph[countryName] = list()
            if countryNeighbourName not in graph[countryName]:
                graph[countryName].append(countryNeighbourName)                

        return graph

    def generateFromAdjacencyArray(self, array):
        graph = {}

        labels = [i for i in array]
        
        upperTriangle = np.triu(array, 1)

        for r, row in enumerate(upperTriangle):
            for c, val in enumerate(row):
                    if r == 0 and c != 0:
                        graph[c] = {'label': labels[c], 'edges':{}}
                        
                    elif r != c and abs(val) < 1 and abs(val) > 0:
                        graph[r]['edges'][c] = {'weight': abs(val)}

        return graph

    @staticmethod
    def getCovidData():
##        url = "https://corona.lmao.ninja/v2/historical/?lastdays=10"
        url = "https://corona.lmao.ninja/v2/historical/?lastdays=all"
        response = requests.request("GET", url, headers={}, data = {})

        return response.json()

    @staticmethod
    def getPercentChange(current, previous):
        if current == previous:
            return 0

        if previous != 0 and current != 0:
            return (current - previous) / previous * 100.0
        if current != 0 and previous == 0:
##            return float("inf") * abs(current) / current;
            return 0
        else:
            return 0

    def searchCountryInGraph(self, country):
        for graphCountry in self.graphCountries:
            search = graphCountry.find(country)

            if search > -1:
                return country

        return False

    @staticmethod
    def removeLowCorrelationEdges(graph):
        newGraph = {}

        for vertice in graph:
            edges = graph[vertice]['edges']
            verticeLable = graph[vertice]['label']

            newGraph[vertice] = {}
            newGraph[vertice]['label'] = verticeLable
            newGraph[vertice]['edges'] = {}
            
            if len(edges) > 10:
                newEdges = {}
                edgesWeights = [edges[i]['weight'] for i in edges] ## list comprehension
                edgesWeightsArray = np.array(edgesWeights)
                threeMaxElementsIndexes = np.argpartition(edgesWeightsArray, -10)[-10:] #using np.argpartition to get the indexes of the 10 max weights
                threeMaxElements = edgesWeightsArray[threeMaxElementsIndexes]

                for edge in edges:
                    if edges[edge]['weight'] in threeMaxElements:
                        newEdges[edge] = {'weight': edges[edge]['weight']}

                        
                newGraph[vertice]['edges'] = newEdges #write the new edges which are in the 10 max weights

        return newGraph
    
    def getCorrelMatrix(self):
        colomnsCountries = []
        countries = {}
        rowIndexes = []
        

        covidData = Graph.getCovidData()

        for countryCount, country in enumerate(covidData):
            previousCaseNumber = 0
            previousCaseDate = ''
            countryName = country['country']

            if self.searchCountryInGraph(countryName) == False or countryName in countries:
                continue

            colomnsCountries.append(countryName) ## append to list with coutries names
            countries[countryName] = [] ## make empty list for every country as as key
            
            for caseCount, caseDate in enumerate(country['timeline']['cases']):
                casesNumber = country['timeline']['cases'][caseDate]

                if countryCount == 0:
                    date = datetime.datetime.strptime(caseDate, '%m/%d/%y').strftime('%d/%m/%y')
                    rowIndexes.append(date) ## append all dates to list rowIndexes

                yesterdayAndTodayCasesPercentChange = Graph.getPercentChange(casesNumber, previousCaseNumber)    
                countries[countryName].append(yesterdayAndTodayCasesPercentChange)

                ##updating previous case vars
                previousCaseNumber = casesNumber
                previousCaseDate = caseDate

        df = pd.DataFrame(countries, columns = colomnsCountries, index=rowIndexes)
        df.to_excel("output.xlsx")
        
        corrDF = df.corr(method ='pearson')
        
        corrDF.to_excel("corr_output.xlsx")
        
        print ('DFs Exported')
        return corrDF

    
    def getMatchedGraph(self, countriesNeighboursGraph, covidCorrGraph):
        countriesNeighboursGraphEdges = {}
        covidCorrGraphEdges = {}
        res = {}

        for vertice in covidCorrGraph:
            edges = covidCorrGraph[vertice]['edges']
            sourceLabel = covidCorrGraph[vertice]['label']
            
            for edge in edges:
                targetLabel = covidCorrGraph[edge]['label']

                if sourceLabel in countriesNeighboursGraph:
                    for ed in countriesNeighboursGraph[sourceLabel]:
                        if targetLabel == ed:
                            if sourceLabel not in res:
                                res[sourceLabel] = []
                                res[sourceLabel].append(targetLabel)
                            else:
                                res[sourceLabel].append(targetLabel)

                                


        return res
                            

                
        
        
  

print('Starting to generate the coutries neighbours graph')

newGraph = Graph('GEODATASOURCE-COUNTRY-BORDERS.csv')
countriesNeighboursGraph = newGraph.generate()

export = Export(countriesNeighboursGraph)
export.toGEXF(True)

print()
print('------------------------------------')
print()
print('Starting to generate the covid cases correlation graph')

corrArray = newGraph.getCorrelMatrix()
corrGraph = newGraph.generateFromAdjacencyArray(corrArray)

covidCorrGraph = newGraph.removeLowCorrelationEdges(corrGraph)

export = Export(covidCorrGraph)
export.toGEXF(False)

print()
print('------------------------------------')
print()
print('Starting to generate the result graph')

resGraph = newGraph.getMatchedGraph(countriesNeighboursGraph, covidCorrGraph)

export = Export(resGraph)
export.toGEXF(True)