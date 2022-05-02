import matplotlib.pyplot as plt
import mysql.connector
import schedule
import numpy as np
from mip import Model, BINARY, maximize, xsum
from multiprocessing import Process
import smtplib
from utils import Schedule
from pyschedule import Scenario , solvers , plotters
import mysql.connector
from closed_loop_oed import BayesGap
from app import closed_loop_opt
import os
import pickle
from datetime import datetime,timedelta
from sim_with_seed import sim

from app import policies_gen
now = datetime.now()

# EV pre-stored dataset
EVdata = {
    "Tesla Model 3" : [150 , 82000 , 450] ,
    "Hyundai Ioniq Electric" : [160 , 38300 , 273] ,
    "BMW i3 BEV" : [170 , 42200 , 252] ,
    "Chevrolet Bolt EV" : [170 , 60000 , 400] ,
    "Tata Nexon EV" : [140 , 30000 , 216] ,
    "MG ZS EV" : [130 , 44500 , 340]
}

# station capacity -> 45kW
# charging point capacity -> 7.5kW
# voltage at CC -> 240V
# Maximum current -> 31.25A
class ItemValue:
 
    """Item Value DataClass"""
 
    def __init__(self, wt, val, ind):
        self.wt = wt
        self.val = val
        self.ind = ind
        self.cost = val // wt
 
    def __lt__(self, other):
        return self.cost < other.cost
 

class BatteryDemand:

    def current(self,SoC,fast):
        SoC/=100
        if fast==0:
            for i in range(1 , 5) :
                closed_loop_opt(i)
            print("Check in fast loop")
            #y=self.fast_current_calc(1)
            with open ('lifetime_best', 'rb') as fp:
                y = pickle.load(fp)
            print(y)
            if y is not None:
                if SoC<0.2:
                    return y[0]*20
                elif 0.2<=SoC<0.4:
                    return y[1]*20
                elif 0.4<=SoC<0.6:
                    return y[2]*20
                elif 0.6<=SoC<0.8:
                    return y[3]*20
                elif 0.8<=SoC:
                    return y[4]*20
        if SoC < 0.8:
            return 18.75
        else:
            return 18.75*np.exp(0.8-SoC)/3

    def voltage(self,SoC,fast):
        SoC /=100
        if SoC < 0.8:
            return 50*SoC + 390
        else:
            return 400

def power(car):

    print(car)
    EVdata = {
    "Tesla Model 3" : [0.15 , 82000 , 450] ,
    "Hyundai Ioniq Electric" : [0.16 , 38300 , 273] ,
    "BMW i3 BEV" : [0.17 , 42200 , 252] ,
    "Chevrolet Bolt EV" : [0.17 , 60000 , 400] ,
    "Tata Nexon EV" : [0.14 , 30000 , 216] ,
    "MG ZS EV" : [0.13 , 44500 , 340]}
    bat_capacity=82000
    print(bat_capacity)

    SoC = car[0]["initial_soc"]
    print(SoC)
    fast=car[0]["fast"]
    SOC_desired=car[0]["final_soc"]
    print(SOC_desired)
    Time_by_user=car[0]["departure_duration_smart"]
    
    
    if fast==0:
        policies_gen(SoC,SOC_desired,Time_by_user,bat_capacity)


    if SoC>=100:
        return 0
    VI = BatteryDemand()
    I = VI.current(SoC,fast)
    V = VI.voltage(SoC,fast)
    P = V*I
    return P

def fillTable_current_values():
    # CREATE DATABASE IF NOT EXISTS DBname
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='evcs'
    )

    cursor = db.cursor(dictionary=True)

    sql = "INSERT INTO current_values (charge_start_time , fast,soct ,departure_duration_smart , power ) VALUES (%s,%s,%s,%s,%s)"
    val = [0,0,0,0,0]

    for i in range(500):
        cursor.execute(sql,val)
    db.commit()

def create_database() :
    # CREATE DATABASE IF NOT EXISTS DBname
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='evcs'
    )

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users(user_id INT AUTO_INCREMENT PRIMARY KEY,user_contact_no CHAR(10),user_email_id CHAR(40) ,fast BOOL ,ev_name CHAR(30) ,initial_soc INT, requested_km INT,departure_duration_fast TIMESTAMP(0),prescheduled BOOL,final_soc INT,Timeslot CHAR(30) ,departure_duration_smart INT, charge_start_time TIMESTAMP(0) )")
    # # ## create table for schedule and charging point allotment
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS schedule(id INT AUTO_INCREMENT PRIMARY KEY, ts TIMESTAMP(0), CS0 INT, CS1 INT, CS2 INT, CS3 INT, CS4 INT, CS5 INT)")

    db.commit()

def SendEmails():

    def email(user):

        # 1  -> year-month-next_day 00:00:00
        # 96 -> year-month-next_day 23:45:00

        hr_list = list(range(0 , 24))
        min_list = [0 , 15 , 30 , 45]
        relation_list = []
        for i in hr_list :
            for j in min_list :
                relation_list.append("{:02d}:{:02d}".format(i , j))

        db = mysql.connector.connect(
            host="localhost" ,
            user="root" ,
            passwd="mysql@123" ,
            database='EVCS'
        )
        cursor = db.cursor(dictionary=True)

        user_id , station_id , start , end = user

        cursor.execute("select * from users WHERE user_id = {}".format(user_id))
        _ = cursor.fetchall()

        email_id = _[0]["user_email_id"]
        day = "{}-{}-{}".format(now.year, now.month , now.day + 1)

        s = smtplib.SMTP('smtp.gmail.com' , 587)
        s.starttls()
        s.login("leoronaldo578@gmail.com","steam@123")
        message = """From: BTech Project Group 2 <{}>
To: User {} <{}>
Subject: Final Time-slot for EV charging {}

Dear EV user,
    You have been allotted a charging station {}, on {} at {}.
Please report 10 minutes before your timeslot for avoiding delays.
Happy EVing...
            """.format("leoronaldo578@gmail.com" ,user_id, email_id , datetime.now() ,station_id, day,relation_list[start-1],)
        try :
            # sending the mail
            s.sendmail("leoronaldo578@gmail.com" , email_id , message)
            print("Email Sent!")
        except :
            print("Unable to Send Email")
        # terminating the session
        s.quit()

    # Schedule EVs for the last time for a day
    _, schdl = Schedule()

    for user in schdl:
        email(user)

def Priority(cars, SoC_min = 15):
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)

    p1 = [0]*6  
    p2 = [0]*6  
    p3 = [0]*6  
    p4 = [0]*6  
    priority=[0]*6

    # find for each car, running outer loop
    for i in range(len(cars)):

        # condition if slot is empty -> [0,1,3,0,0,4]
        if cars[i]==[]:
            continue

        user_id = cars[i][0]["user_id"]

        fsoc = cars[i][0]["final_soc"]
        isoc = cars[i][0]["initial_soc"]

        if power(cars[i]) ==0:
            priority[i] = - 10^10
            continue
        if fsoc>isoc:
            if cars[i][0]["fast"]:
                p4[i] = 1
            else:
                p4[i] = 0
            if SoC_min>isoc:
                p1[i] = SoC_min - isoc
            else:
                p1[i] = 0
            p3[i] = fsoc-isoc
            bat_capacity=EVdata[cars[i][0]["ev_name"]]
            sql="SELECT * FROM schedule WHERE CS{} = %s LIMIT 1".format(i)
            cursor.execute(sql,(cars[i][0]["user_id"],))
            records=cursor.fetchall()
            time=records[0]["ts"]



            # temp=start_time.strptime("%H:%M:%S")
            now = datetime.now()
            delta_t = now - time
            delta_t = delta_t.total_seconds()
            delta_th = delta_t // 60
            p2[i] = (cars[i][0]["departure_duration_smart"]-delta_th)*100/cars[i][0]["departure_duration_smart"]
        priority[i]=100000*p1[i]+100*p3[i]+10000*p4[i]+1000*p2[i]
   
    return priority

def current_assignment() :

    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)

    if 0<=now.minute <15:
        d = datetime.now().replace(second=0 , microsecond=0,minute=0)
    if 15 <= now.minute < 30 :
        d = datetime.now().replace(second=0 , microsecond=0 , minute=15)
    if 30<=now.minute <45:
        d = datetime.now().replace(second=0 , microsecond=0,minute=30)
    if 45<=now.minute:
        d = datetime.now().replace(second=0 , microsecond=0,minute=45)

    sql = "SELECT * from schedule WHERE ts = %s"
    values = (d,)
    cursor.execute(sql , values)
    record = cursor.fetchone()

    car_ids = []
    for car in range(0,6):
        car_ids.append(record["CS{}".format(car)])

    cars = []
    powers = [0]*6
    # compute priorities


    for id in car_ids:
        sql = "SELECT * from users WHERE user_id = %s"
        cursor.execute(sql,(id,))
        car = cursor.fetchall()
        cars.append(car)


    priority = Priority(cars)

  

    # print(priority)

    # Assign power to the cars for this timeslot

    Total_power = 37500  # actual capacity of a charging station

    for i in range(len(cars)):

        if (cars[i]==[]):
            continue
        # print("check the fucking soc:",cars[i][0])
        powers[i] = power(cars[i])
        #except:
        #    pass


    p = priority
    w = powers
    c , I = Total_power , range(len(w))

    m = Model("knapsack")

    x = [m.add_var(var_type=BINARY) for i in I]

    m.objective = maximize(xsum(p[i] * x[i] for i in I))

    m += xsum(w[i] * x[i] for i in I) <= c

    m.optimize()

    selected = [i for i in I if x[i].x >= 0.99]
    power_utilized = sum([w[i] for i in selected])
    m=0
    weight=0
    print(selected)
    
    if power_utilized < c and len(selected)<6:
        for s in range(len(w)):
            if s not in selected and p[s]>m:
                m=p[s]
                weight=w[s]
                final=s 
        powers[final]=c-power_utilized
        selected.append(final)
    print(selected)

    
    # update current SoC, departure duration in users table
    # update price values in current values table

    for i in selected :
        try:
            if cars[i] != [] :

                user_id = cars[i][0]["user_id"]
                cursor.execute("SELECT * FROM CopyUsers WHERE user_id = %s" , (user_id ,))
                temp_elements = cursor.fetchall()

                SoC = cars[i][0]["initial_soc"]
                P = powers[i]
                C = EVdata[cars[i][0]["ev_name"]][1]

                if SoC>=100:
                    sql = "UPDATE CopyUsers SET initial_soc = %s WHERE user_id = %s"
                    cursor.execute(sql , [100 , user_id])

                if (SoC + (P / C) * 100)>=100:
                    SoC = SoC + (P / C) * 100

                    sql = "UPDATE CopyUsers SET initial_soc = %s WHERE user_id = %s"
                    cursor.execute(sql , [int(SoC) , user_id])

                if cars[i][0]["departure_duration_smart"]<=15:
                    sql = "UPDATE CopyUsers SET departure_duration_smart = %s WHERE user_id = %s"
                    cursor.execute(sql , [0 , user_id])
                else:
                    sql = "UPDATE CopyUsers SET departure_duration_smart = %s WHERE user_id = %s"
                    cursor.execute(sql , [cars[i][0]["departure_duration_smart"]-15 , user_id])

                powert = cars[i][0]["requested_km"]

                if P > 7500 :
                    updated_power = int(powert + 7500)
                else :
                    updated_power = int(powert + P)

                cursor.execute("UPDATE CopyUsers SET requested_km = %s WHERE user_id = %s" , [updated_power , user_id])
        except:
            print("No users found")
    db.commit()

    return selected, powers,priority

def OpenSlots(slots_for_days=1 , year=now.year , month=now.month , day=now.day) :
    hr = list(range(0 , 24))
    min = [0 , 15 , 30 , 45]

    ts = []
    for i in hr :
        for j in min :
            ts.append("{:02d}:{:02d}".format(i , j) + ":00")

    slots = []

    for today in range(1 , slots_for_days + 1) :
        for k in ts:

            slots.append("{}-{:02d}-{:02d} ".format(year, 5,1+today) + k)

    val = []

    for slot in slots :
        val.append([slot , 0 , 0 , 0 , 0 , 0 , 0])

    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database="EVCS"
    )

    # preparing a cursor object

    cursor = db.cursor(dictionary=True)

    val = []

    for slot in slots :
        val.append((slot , 0 , 0 , 0 , 0 , 0 , 0))

    for row in val :
        cursor.execute("INSERT INTO schedule (ts,CS0,CS1,CS2,CS3,CS4,CS5) VALUES (%s,%s,%s,%s,%s,%s,%s)" , row)
    db.commit()
    # print("Slots created for {}-{}-{}".format(now.year , now.month , now.day + 1))

def scheduler():

    print("New slots for next day are opened at 11 PM")
    # Slots for the next day have been created
    schedule.every().day.at("23:00").do(OpenSlots)

    # Today's slots have been emailed the the users
    schedule.every().day.at("23:30").do(SendEmails)

    #run at 00,15,30,45 mins whole day

    for hr in range(0,24):
        for min in [0,15,30,45]:
            schedule.every().day.at("{:02d}:{:02d}".format(hr,min)).do(current_assignment)

    # Task scheduling
    # After every 10mins geeks() is called.

    while True :
        # Checks whether a scheduled task
        # is pending to run or not
        schedule.run_pending()

def main():

    # create database 'evcs' and tables 'users' and 'schedule' if do not exist already

    create_database()

    t1=Process(target=scheduler)
    print("Threading started")
    t1.start()
    print("Current assignment process started in the background...\nFunction runs after every 15 minutes\nYou are free to add New EVs in real time for today or pre-book the slots for tomorrow ")
    # open GUI
    import GUI_and_Functions




##################################################################
def Schedule_flexible(date = '2022-04-26'):
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)
    date = "{} 00:00:00".format(date)
    cursor.execute("select * from users WHERE charge_start_time = %s" ,
                   (date,))
    users = cursor.fetchall()

    S = Scenario('Prescheduling' , horizon=97)
    CS = S.Resources('CS' , num=6 , is_group=True)

    ev = []

    try :

        for user in users :

            # 1  -> year-month-next_day 00:00:00
            # 96 -> year-month-next_day 23:45:00

            hr_list = list(range(0 , 24))
            min_list = [0 , 15 , 30 , 45]
            relation_list = []
            for i in hr_list :
                for j in min_list :
                    relation_list.append("{:02d}:{:02d}".format(i , j))

            # extract data from user tuple

            user_id = user["user_id"]
            ev_name = user["ev_name"]

            if user["Timeslot"] == "12 AM to 3 AM" :
                p = [1 , 13]
            if user["Timeslot"] == "3 AM to 6 AM" :
                p = [13 , 25]
            if user["Timeslot"] == "6 AM to 9 AM" :
                p = [25 , 37]
            if user["Timeslot"] == "9 AM to 12 PM" :
                p = [37 , 49]
            if user["Timeslot"] == "12 PM to 3 PM" :
                p = [49 , 61]
            if user["Timeslot"] == "3 PM to 6 PM" :
                p = [61 , 73]
            if user["Timeslot"] == "6 PM to 9 PM" :
                p = [73 , 85]
            if user["Timeslot"] == "9 PM to 12 AM" :
                p = [85 , 97]

            car = S.Task("{}".format(user_id) , length=round(user["departure_duration_smart"] / 15) , delay_cost=1)
            S += car > p[0] , car < p[1]
            ev.append(car)

        for car in ev :
            car += CS[0] | CS[1] | CS[2] | CS[3] | CS[4] | CS[5]

        solvers.mip.solve(S , msg=1 , random_seed=0)

        if len(S.solution()) == 0 :
            print("No Slot")
            return False , []
        if len(S.solution()) != 0 :
            # Insert into schedule
            for car in S.solution() :
                id = car[0]
                CS = str(car[1])

                for insert in range(car[2] , car[3] + 1) :
                    ts = "{}-{}-{} {}:00".format(now.year , now.month , now.day + 1 , relation_list[insert - 1])
                    cursor.execute("UPDATE schedule SET {} = {} WHERE ts='{}'".format(CS , id , ts))

            plotters.matplotlib.plot(S , img_filename='prescheduled_chart_flexible.png')
            db.commit()
    except:
        print("No users found")

def current_assignment_flexible(timeslot):
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)

    # collect all car user_id s for this timeslot
    sql = "SELECT * from schedule WHERE ts = %s"
    values = (timeslot ,)
    cursor.execute(sql , values)
    record = cursor.fetchone()

    car_ids = []
    for point in range(0, 6):
        try:
            car_ids.append(record["CS{}".format(point)])
        except:
            print("No schedule")

    # check which users are present now

    # print(car_ids)

    # some dummy variables and initializations

    cars = []
    powers = [0] * 6
    Total_power = 37500 # actual capacity of a charging station
    # compute priorities


    for user_id in car_ids :
        sql = "SELECT * from CopyUsers WHERE user_id = %s"
        cursor.execute(sql , (user_id ,))
        car = cursor.fetchall()
        cars.append(car)

    priority = Priority(cars)

    # print(priority)

    # Assign power to the cars for this timeslot

    for i in range(len(cars)) :

        if (cars[i] == []) :
            continue
        powers[i] = power(cars[i])

    print("Power demanded by points:",powers)

    #..........................MIP..............................
    p = priority
    w = powers
    c , I = Total_power , range(len(w))

    m = Model("knapsack")

    x = [m.add_var(var_type=BINARY) for i in I]

    m.objective = maximize(xsum(p[i] * x[i] for i in I))

    m += xsum(w[i] * x[i] for i in I) <= c

    m.optimize()

    selected = [i for i in I if x[i].x >= 0.99]


    power_utilized = sum([w[i] for i in selected])
    m = 0
    weight = 0
    if power_utilized < 0.95 * c and len(selected) < 6 :
        deltaP = c - power_utilized
        for point in range(6) :
            if point not in selected :
                if deltaP>powers[point]:
                    selected.append(point)
                else:
                    selected.append(point)
                    powers[point] = deltaP


    print("Selected points for power assignment:",selected)

    # update current SoC, departure duration in current_values table
    # update power values in current_values table

    # cars list = [[{}],[{}],[{}],[{}],[{}],[{}]]

    for i in selected :
        try:
            if cars[i] != [] :

                user_id = cars[i][0]["user_id"]
                cursor.execute("SELECT * FROM CopyUsers WHERE user_id = %s" , (user_id ,))
                temp_elements = cursor.fetchall()

                SoC = cars[i][0]["initial_soc"]
                P = powers[i]
                C = EVdata[cars[i][0]["ev_name"]][1]

                if SoC>=100:
                    sql = "UPDATE CopyUsers SET initial_soc = %s WHERE user_id = %s"
                    cursor.execute(sql , [100 , user_id])

                if (SoC + (P / C) * 100)>=100:
                    SoC = SoC + (P / C) * 100

                    sql = "UPDATE CopyUsers SET initial_soc = %s WHERE user_id = %s"
                    cursor.execute(sql , [int(SoC) , user_id])

                if cars[i][0]["departure_duration_smart"]<=15:
                    sql = "UPDATE CopyUsers SET departure_duration_smart = %s WHERE user_id = %s"
                    cursor.execute(sql , [0 , user_id])
                else:
                    sql = "UPDATE CopyUsers SET departure_duration_smart = %s WHERE user_id = %s"
                    cursor.execute(sql , [cars[i][0]["departure_duration_smart"]-15 , user_id])

                powert = cars[i][0]["requested_km"]

                if P > 7500 :
                    updated_power = int(powert + 7500)
                else :
                    updated_power = int(powert + P)

                cursor.execute("UPDATE CopyUsers SET requested_km = %s WHERE user_id = %s" , [updated_power , user_id])
        except:
            print("No users found")
    db.commit()

    return selected, powers,priority


def demo() :
    #########################################################################################################
    # Demo of the current assignment
    # function has been modified to take timeslot as argument
    # original fucntion -> current_assignment()
    # new function -> current_assignment_flexible(timeslot)

    # demo for the day : 2022-04-28

    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)

    # copy all initial data to current values plot

    #
    cursor.execute("DROP TABLE CopyUsers")
    query = "CREATE TABLE CopyUsers SELECT * FROM Users"
    cursor.execute(query)

    # fetch all schedule entries for this day

    date = datetime(2022 , 4 , 28 , 0 , 0 , 0)
    end = date + timedelta(1)

    cursor.execute("SELECT * FROM schedule WHERE ts>=%s and ts<%s" , (date , end))
    rows = cursor.fetchall()

    # looping through the day
    power_supplied = np.zeros([96 , 6])
    all_priorites = []

    for i in range(len(rows)) :
        # find power delivary and assignment
        selected , powers , priority = current_assignment_flexible(rows[i]["ts"])
        # feed this data in power supplied matrix
        all_priorites.append(priority)
        for j in selected :
            power_supplied[i][j] = powers[j]

    # print(all_priorites)
    # print(power_supplied)

    maximum_use = np.ones([96 , 5]) * 7500

    usage = sum(sum(power_supplied)) / sum(sum(maximum_use)) * 100
    wastage = (sum(sum(maximum_use)) - sum(sum(power_supplied))) / sum(sum(maximum_use)) * 100

    print("Result from Smart charging algorithm:\nPower utilized:{}%\nPower wasted:{}%".format(usage,wastage))

    CS0 = []
    CS1 = []
    CS2 = []
    CS3 = []
    CS4 = []
    CS5 = []
    total_power = []
    for row in range(96) :
        CS0.append(power_supplied[row][0])
        CS1.append(power_supplied[row][1])
        CS2.append(power_supplied[row][2])
        CS3.append(power_supplied[row][3])
        CS4.append(power_supplied[row][4])
        CS5.append(power_supplied[row][5])
        total_power.append(power_supplied[row][0]+power_supplied[row][1]+power_supplied[row][2]+power_supplied[row][3]+power_supplied[row][4]+power_supplied[row][5])

    x = list(range(96))
    # make all plots

    #CS0
    plt.subplot(7,1,1)
    plt.plot(x , CS0 , label='CS0')
    plt.title("CS0")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.subplot(7,1,2)
    plt.plot(x , CS1 , label='CS1')
    plt.title("CS1")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.subplot(7,1,3)
    plt.plot(x , CS2 , label='CS2')
    plt.title("CS2")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.subplot(7,1,4)
    plt.plot(x , CS3 , label='CS3')
    plt.title("CS3")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.subplot(7,1,5)
    plt.plot(x , CS4 , label='CS4')
    plt.title("CS4")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.subplot(7 ,1,6)
    plt.plot(x , CS5 , label='CS5')
    plt.title("CS5")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.show()

    plt.plot(x , total_power , label='Total',color = 'y')
    plt.plot(x,37500*np.ones(len(x)),label="threshold (37.5 kW)",color='r',linestyle = 'dotted')
    plt.title("Total power delivered to EVs for a day. A charging station of 5 charging point capacity has been extended to work as 6 charging point station")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    return total_power

    #plt.show()


def demo_normal():
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)

    date = datetime(2022 , 4 , 28 , 0 , 0 , 0)
    end = date + timedelta(1)

    cursor.execute("DROP TABLE CopyUsers")
    cursor.execute("CREATE TABLE CopyUsers SELECT * FROM Users")

    # get this days schedule from table
    cursor.execute("SELECT * FROM schedule WHERE ts>=%s and ts<%s" , (date , end))
    slots = cursor.fetchall()

    # looping through the day

    # Now station has 6 points
    # Each of power 7.5kW
    Total_power = 45000
    distribute_power = np.zeros([96,6])

    for i in range(len(slots)):

        # list down all cars connected to this timeslot
        cars = [0]*6
        for j in range(6):
            if slots[i]["CS{}".format(j)]!=0:
                cars[j] = (slots[i]["CS{}".format(j)])

        # get power required by cars in this timeslot

        for j in range(6):
            user_id = cars[j]
            if user_id==0:
                continue
            cursor.execute("SELECT * FROM CopyUsers WHERE user_id=%s" , (user_id,))
            car = cursor.fetchall()
            P = power(car)
            SoC = car[0]["initial_soc"]

            C = EVdata[car[0]["ev_name"]][1]
            if P>7500:
                P=7500

            distribute_power[i][j] = P
            if SoC >= 100 :
                    cursor.execute("UPDATE CopyUsers SET initial_soc = %s WHERE user_id = %s" , [100 , user_id])

            if (SoC + (P / C) * 100) <= 100 :
                SoC = SoC + (P / C) * 100
                cursor.execute("UPDATE CopyUsers SET initial_soc = %s WHERE user_id = %s" , [int(SoC) , user_id])

            if P > 7500 :
                updated_power = int(car[0]["requested_km"] + 7500)
            else :
                updated_power = int(car[0]["requested_km"] + P)

            cursor.execute("UPDATE CopyUsers SET requested_km = %s WHERE user_id = %s" , [updated_power , user_id])

    # maths to find power utilization and wastage results

    maximum_use = np.ones([96,6])*7500

    usage = sum(sum(distribute_power)) / sum(sum(maximum_use)) * 100
    wastage = (sum(sum(maximum_use)) - sum(sum(distribute_power))) / sum(sum(maximum_use)) * 100

    print("Result from Normal charging algorithm:\nPower utilized:{}%\nPower wasted:{}%".format(usage , wastage))


    CS0 = []
    CS1 = []
    CS2 = []
    CS3 = []
    CS4 = []
    CS5 = []
    total_power = []
    for row in range(96) :
        CS0.append(distribute_power[row][0])
        CS1.append(distribute_power[row][1])
        CS2.append(distribute_power[row][2])
        CS3.append(distribute_power[row][3])
        CS4.append(distribute_power[row][4])
        CS5.append(distribute_power[row][5])
        total_power.append(
            distribute_power[row][0] + distribute_power[row][1] + distribute_power[row][2] + distribute_power[row][3] +
            distribute_power[row][4] + distribute_power[row][5])

    x = list(range(96))
    # make all plots

    # CS 0
    # plt.subplot(7 , 1 , 1)
    # plt.plot(x , CS0 , label='CS0')
    # plt.title("CS0")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #
    # plt.subplot(7 , 1 , 2)
    # plt.plot(x , CS1 , label='CS1')
    # plt.title("CS1")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #
    # plt.subplot(7 , 1 , 3)
    # plt.plot(x , CS2 , label='CS2')
    # plt.title("CS2")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #
    # plt.subplot(7 , 1 , 4)
    # plt.plot(x , CS3 , label='CS3')
    # plt.title("CS3")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #
    # plt.subplot(7 , 1 , 5)
    # plt.plot(x , CS4 , label='CS4')
    # plt.title("CS4")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #
    # plt.subplot(7 , 1 , 6)
    # plt.plot(x , CS5 , label='CS5')
    # plt.title("CS5")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #
    # #plt.show()
    #
    # plt.plot(x , total_power , label='Total' , color='y')
    # plt.plot(x , 45000 * np.ones(len(x)) , label="threshold (45 kW)" , color='r' , linestyle='dotted')
    # plt.title(
    #     "Total power delivered to EVs for a day. Normal charging with 6 points capacity")
    # plt.xlabel("Time(day)")
    # plt.ylabel("Power(W)")
    # plt.legend()
    #plt.show()
    return total_power

def PowerVsSoC():
    P= [0]*100
    soc = list(range(1,101))

    for i in range(100):
        P[i] = power(soc[i])

    plt.plot(soc,P)
    plt.show()



if __name__ == '__main__':
    # main()
    Psmart = demo()

    Pnormal = demo_normal()
    # PowerVsSoC()
    # main()
    x = list(range(96))
    plt.subplot(2,1,1)
    plt.plot(x , Psmart , label='Smart algo' , color='y')
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()

    plt.subplot(2 , 1 , 2)
    plt.plot(x , Pnormal , label="Normal" , color='r')
    plt.title(
        "Total power delivered to EVs for a day. Normal charging vs Smart algorithm")
    plt.xlabel("Time(day)")
    plt.ylabel("Power(W)")
    plt.legend()
    plt.show()





