from pyschedule import Scenario , solvers , plotters
import mysql.connector
from datetime import datetime , timedelta

now = datetime.now()

def schedule_cost_reward(user):
    reward=0
    if user["fast"]:
        reward+=100
    reward+=user["initial_soc"]-user["final_soc"]
    return reward

def Schedule() :
    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )
    cursor = db.cursor(dictionary=True)
    cursor.execute("select * from users WHERE charge_start_time = %s",(datetime.now().replace(hour=0,minute=0,microsecond=0 , second=0)+timedelta(1),))
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

        print(S.solution())

        if len(S.solution()) == 0 :
            print("No Slot")
            return False, []
        if len(S.solution()) != 0 :
            # Insert into schedule
            for car in S.solution() :
                id = car[0]
                CS = str(car[1])

                for insert in range(car[2] , car[3] + 1) :
                    ts = "{}-{}-{} {}:00".format(now.year , now.month , now.day + 1 , relation_list[insert - 1])
                    cursor.execute("UPDATE schedule SET {} = {} WHERE ts='{}'".format(CS , id , ts))

            plotters.matplotlib.plot(S , img_filename='prescheduled_chart.png')
            db.commit()
            return True, S.solution()
    except:
        print("No users found")
