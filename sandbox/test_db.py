__author__ = 'himanshu'
import psycopg2

try:
    conn = psycopg2.connect("dbname='sync' user='himanshu' host='/var/run/postgresql' password=''")
except:
    print "I am unable to connect to the database"