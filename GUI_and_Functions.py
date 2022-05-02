from datetime import datetime , timedelta
from tkinter import *
from tkinter.ttk import *
import tkinter.font as tkFont
from PIL import Image , ImageTk
import smtplib
from app import policies_gen
from app import closed_loop_opt
from twilio.rest import Client
import mysql.connector
from system import current_assignment
from utils import Schedule

# compute today's datetime
now = datetime.now()


def SendEmailFast(data , emailid , cost , isoc , request , time) :
    s = smtplib.SMTP('smtp.gmail.com' , 587)
    s.starttls()
    s.login("leoronaldo578@gmail.com" , "steam@123")
    message = """From: From BTech Project Group 2 <{}>
    To: <{}>   
    Subject: Fast charging Session {}

    Your Vehicle has been connected to Fast charging facility. 
    User Details:
    EV model : {}
    Initial SoC : {}
    Requested kms : {}
    Tentative Departure time : {}

    Your Cost for the current session : {}

    Happy EVing...
    """.format("leoronaldo578@gmail.com" , emailid , datetime.now() , data["Name"] , isoc , request , time ,
               round(cost))
    try :
        # sending the mail
        s.sendmail("leoronaldo578@gmail.com" , emailid , message)
        print("Email Sent!")
    except :
        print("Unable to Send Email")
    # terminating the session
    s.quit()


def SendSMSFast(data , emailid , cost , isoc , request , time , phoneno) :
    try:
        # Your Account Sid and Auth Token from twilio account
        account_sid = "AC6f929fdc7e443ddccad63b856b0c49e8"
        auth_token = "b36df784cacfd6ce0a6fe2dfb1678282"
        # instantiating the Client
        client = Client(account_sid , auth_token)
        # sending message
        message = client.messages.create(
            body="""From: From BTech Project Group 2 <{}>
        To: <{}>   
        Subject: Fast charging Session {}
    
        Your Vehicle has been connected to Fast charging facility. 
        User Details:
        EV model : {}
        Initial SoC : {}
        Requested kms : {}
        Tentative Departure time : {}
    
        Your Cost for the current session : {}
    
        Happy EVing...
        """.format("leoronaldo578@gmail.com" , emailid , datetime.now() , data["Name"] , isoc , request , time ,
                   round(cost)) ,
            from_="+19896327385" ,
            to='+91{}'.format(phoneno))
        # printing the sid after success
        try:
            print(message.sid)
            print("Message Sent")
        except:
            print("Unable to send SMS")
    except:
        print("Unable to Send SMS")


def FindCost() :
    data = {"EmailID" : variable_Email_id.get() ,
            "PhoneNo" : variable_Phone_No.get() ,
            "Name" : variable_EVtype_main_window.get() ,
            "InitialSoC" : variable_initialSoC_main_window.get() ,
            "Requestedkm" : variable_requestedkm_main_window.get() ,
            "RequestedTime" : variable_requestedtime_main_window.get() ,
            }

    # Calculate Desired value of SoC
    emailid = data["EmailID"]
    phoneno = data["PhoneNo"]
    request = data["Requestedkm"]
    isoc = data["InitialSoC"]
    wperkm = EVdata[data["Name"]][0] * 1000
    C = EVdata[data["Name"]][1]
    maxrange = EVdata[data["Name"]][2]
    time = data["RequestedTime"]

    if isoc < 0 or isoc > 100 :
        print("Invalid SoC Entered")
        return
    if request < 0 :
        print("Invalid Km number Entered")
        return
    if time < 0 :
        print("Invalid Time Entered")
        return
    if request <= maxrange :
        fsoc = (C * (isoc / 100) + wperkm * request) * 100 / C
        cost = policies_gen(isoc / 100 , fsoc / 100 , time , C)
        # for i in range(1 , 5) :
        #     closed_loop_opt(i)

        SendEmailFast(data , emailid , cost , isoc , request , time)
        SendSMSFast(data , emailid , cost , isoc , request , time , phoneno)

    else :

        print("type again")

def Insert_into_users() :
   
    data = {"charging_mode" : variable_charging_mode.get() ,
            "smart_charging_mode" : variable_prescheduled_charging.get() ,
            "ev_name" : variable_EVtype_smart_charging.get() ,
            "initial_soc" : variable_initialSoC_smart_charging.get() ,
            "final_soc" : variable_finalSoC_smart_charging.get() ,
            "timeslot" : variable_timeslot.get() ,
            "RequestedTime" : variable_requestedtime_smart_charging.get()
            }

    db = mysql.connector.connect(
        host="localhost" ,
        user="root" ,
        passwd="mysql@123" ,
        database='EVCS'
    )

    cursor = db.cursor(dictionary=True)

    # Insert user data into User table
    maxrange = EVdata[data["ev_name"]][2]
    wperkm = EVdata[data["ev_name"]][0] * 1000
    C = EVdata[data["ev_name"]][1]
    time = data["RequestedTime"]
    request_km = data["final_soc"]   #requrest kms after changed gui
    isoc = data["initial_soc"]

    if isoc < 0 or isoc > 100 :
        print("Invalid SoC Entered")
        return
    if request_km < 0 :
        print("Invalid Km number Entered")
        return
    if time < 0 :
        print("Invalid Time Entered")
        return
    if request_km <= maxrange :
        fsoc = (C * (isoc / 100) + wperkm * request_km) * 100 / C

        if fsoc >=100:
            fsoc=100

    else:
        fsoc = 100
        

    # Pre-scheduled user

    if variable_prescheduled_charging.get() :

        sql = "INSERT INTO Users (user_contact_no,user_email_id,fast,ev_name ,initial_soc,requested_km,prescheduled,final_soc,Timeslot,departure_duration_smart,charge_start_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        val = [
            variable_Phone_No.get() ,
            variable_Email_id.get() ,
            variable_charging_mode.get() ,
            data["ev_name"] ,
            data["initial_soc"] ,
            variable_requestedkm_main_window.get() ,
            data["smart_charging_mode"] ,
            fsoc ,
            variable_timeslot.get() ,
            data["RequestedTime"],
            datetime.now().replace(hour=0,minute=0,microsecond=0 , second=0)+timedelta(1)
        ]
        cursor.execute(sql , val)
        db.commit()
        id = cursor.lastrowid

        #if schedule returns false, _
        truth, _ = Schedule()
        if truth is False :
            #cursor.execute(sql , val)
            cursor.execute("DELETE FROM `evcs`.`users` WHERE (`user_id` = '{}')".format(id))
            db.commit()
        else :

            return

    # Real-time user

    else :
        sql = "INSERT INTO Users (user_contact_no,user_email_id,fast,ev_name ,initial_soc,requested_km,prescheduled,final_soc,Timeslot,departure_duration_smart,charge_start_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        val = [
            variable_Phone_No.get() ,
            variable_Email_id.get() ,
            variable_charging_mode.get() ,
            data["ev_name"] ,
            data["initial_soc"] ,
            variable_requestedkm_main_window.get() ,
            data["smart_charging_mode"] ,
            fsoc ,
            variable_timeslot.get() ,
            data["RequestedTime"] ,
            datetime.now().replace(microsecond=0 , second=0)
        ]

        temp=int(val[9])//15
        interval= 15*temp

        start = val[10] + (datetime.min - val[10]) % timedelta(minutes=15)
        end = start + timedelta(minutes=interval)

        sql_for_check_schedule = """SELECT * FROM schedule WHERE ts BETWEEN %s AND %s"""
        cursor.execute(sql_for_check_schedule , (start , end))
        selected_timeslot = cursor.fetchall()
        print(selected_timeslot)

        request = int(val[9] / 15)
        d = {"CS0" : 0 , "CS1" : 0 , "CS2" : 0 , "CS3" : 0 , "CS4" : 0 , "CS5" : 0}

        for slot in selected_timeslot :
            for key , value in slot.items() :
                if key in d.keys() :
                    if value is None or value == 0 :
                        d[key] += 1
            for key , value in d.items() :

                if (request <= value) :

                    # add user to users table

                    cursor.execute(sql,val)
                    user_id = cursor.lastrowid
                    cursor.execute("UPDATE schedule SET  {} =%s WHERE ts BETWEEN %s and %s".format(key) ,
                                   (user_id , start,end))
                    db.commit()
                    print("realtime added")

                    return True
                    break
        return False


# EV pre-stored dataset
EVdata = {
    "Tesla Model 3" : [0.15 , 82000 , 450] ,
    "Hyundai Ioniq Electric" : [0.16 , 38300 , 273] ,
    "BMW i3 BEV" : [0.17 , 42200 , 252] ,
    "Chevrolet Bolt EV" : [0.17 , 60000 , 400] ,
    "Tata Nexon EV" : [0.14 , 30000 , 216] ,
    "MG ZS EV" : [0.13 , 44500 , 340]
}

# Tkinter GUI initialized
main_window = Tk()

# .get() variables
variable_Email_id = StringVar()
variable_Phone_No = StringVar()
variable_charging_mode = BooleanVar()
variable_EVtype_main_window = StringVar()
variable_initialSoC_main_window = IntVar()
variable_requestedkm_main_window = IntVar()
variable_requestedtime_main_window = IntVar()
variable_prescheduled_charging = BooleanVar()
variable_EVtype_smart_charging = StringVar()
variable_initialSoC_smart_charging = IntVar()
variable_finalSoC_smart_charging = IntVar()
variable_timeslot = StringVar()
variable_requestedtime_smart_charging = IntVar()
# Front End code
# window -> Front End
main_window.resizable(False , False)
main_window.geometry("+150+150")
main_window.configure(bg='#CBF0F0')
main_window.title("EVCS interface")



canvas_top = Canvas(main_window , bg='#41AEF5' , width=2000 , height=140)
canvas_top.place(anchor=N)
panel_info = LabelFrame(main_window , text='Details')
panel_info.grid(row=1 , column=0 , padx=10 , pady=10 , sticky=NSEW)
panel_charging_mode = LabelFrame(main_window , text='Charging Mode')
panel_charging_mode.grid(row=1 , column=1 , padx=10 , pady=10 , sticky=NSEW)
panel_fastcharging = LabelFrame(main_window , text='Fast Charging  cost estimator')
panel_fastcharging.grid(row=2 , column=0 , padx=10 , pady=10 , sticky=NSEW)
panel_smartcharging = LabelFrame(main_window , text='Smart Charging')
panel_smartcharging.grid(row=2 , column=1 , padx=10 , pady=10 , sticky=NSEW)

# College Name
label_collegename = Label(main_window , text='College of Engineering, Pune' , font=tkFont.Font(size=12))
label_collegename.grid(row=0 , column=0 , sticky=SW , padx=10)
label_collegename.config(background='#41AEF5')
label_project_partners = Label(main_window ,
                               text='      B.Tech. Project\nunder the guidance of\n\n     Dr. Meera Murali\n                by\n\n'
                                    '      Sakshi Kulkarni\n    Yashodhan Jaltare\n    Sumeet Gawande')
label_project_partners.configure(anchor="center")
label_project_partners.config(background='#41AEF5')
label_project_partners.grid(row=0 , column=1 , padx=2 , pady=2 , sticky=EW)

image = Image.open("coep.png")
logo = image.resize((90 , 90))
img = ImageTk.PhotoImage(logo)
label_logo = Label(image=img)
label_logo.grid(row=0 , column=0 , sticky=W , pady=14 , padx=70)
main_window.iconbitmap('logo.ico')

# Personal details
label_Email = Label(panel_info , text="Your Email Id:")
label_Email.grid(row=0 , column=0 , padx=2 , pady=2 , sticky="e")

label_phonenumber = Label(panel_info , text="Your Phone No.(+91):")
label_phonenumber.grid(row=1 , column=0 , padx=2 , pady=2 , sticky="e")

entry_Email = Entry(panel_info , textvariable=variable_Email_id)
entry_Email.grid(row=0 , column=1 , padx=2 , pady=2 , sticky="e")

entry_phonenumber = Entry(panel_info , textvariable=variable_Phone_No)
entry_phonenumber.grid(row=1 , column=1 , padx=2 , pady=2 , sticky="e")

radiobutton_slow = Radiobutton(panel_charging_mode , text="Slow Charging (> 1 hr, < 80 A)" , variable=variable_charging_mode , value=0)
radiobutton_slow.grid(row=0 , column=1 , padx=2 , pady=2)
radiobutton_fast = Radiobutton(panel_charging_mode , text="Fast Charging (< 1 hr, > 80 A)" , variable=variable_charging_mode , value=1)
radiobutton_fast.grid(row=0 , column=2 , padx=2 , pady=2)

# Select Car Model
label_Evtype = Label(panel_fastcharging , text='Select EV model:')
label_Evtype.grid(row=0 , column=0 , padx=2 , pady=2 , sticky="e")
options_EVtype = [
    "Tata Nexon EV" ,
    "Tesla Model 3" ,
    "Hyundai Ioniq Electric" ,
    "BMW i3 BEV" ,
    "Chevrolet Bolt EV" ,
    "MG ZS EV"
]

optionmenu_EVtype = OptionMenu(panel_fastcharging , variable_EVtype_main_window , options_EVtype[1] , *options_EVtype)
optionmenu_EVtype.grid(row=0 , column=1 , padx=2 , pady=2)

# inputs provided by user for fast charging
label_initialSoC = Label(panel_fastcharging , text='Initial SoC( in %):')
label_initialSoC.grid(row=1 , column=0 , padx=2 , pady=2 , sticky="e")
entry_nitialSoC = Entry(panel_fastcharging , textvariable=variable_initialSoC_main_window)
entry_nitialSoC.grid(row=1 , column=1 , padx=2 , pady=2 , sticky=SW)

label_requestedkm = Label(panel_fastcharging , text='Requested kms:')
label_requestedkm.grid(row=2 , column=0 , padx=2 , pady=2 , sticky=E)
entry_requestedkm = Entry(panel_fastcharging , textvariable=variable_requestedkm_main_window)
entry_requestedkm.grid(row=2 , column=1 , padx=2 , pady=2 , sticky=SW)

label_requestedtime = Label(panel_fastcharging , text='available duration(min):')
label_requestedtime.grid(row=3 , column=0 , padx=2 , pady=2 , sticky=E)
entry_requestedtime = Entry(panel_fastcharging , textvariable=variable_requestedtime_main_window)
entry_requestedtime.grid(row=3 , column=1 , padx=2 , pady=2 , sticky=SW)

button_findfastchargingcost = Button(panel_fastcharging , text="Find estimated cost" , command=lambda : FindCost())
button_findfastchargingcost.grid(row=6 , column=0 , padx=2 , pady=2 , sticky=EW)

label_smartchargingtype = Label(panel_smartcharging , text='Smart Charging Type :')
label_smartchargingtype.grid(row=0 , column=0 , padx=2 , pady=2 , sticky="e")

radiobutton_pred = Radiobutton(panel_smartcharging , text="Prescheduled Charging" ,
                               variable=variable_prescheduled_charging , value=1)
radiobutton_pred.grid(row=0 , column=1 , padx=2 , pady=2 , sticky="w")
radiobutton_real = Radiobutton(panel_smartcharging , text="Realtime Charging" ,
                               variable=variable_prescheduled_charging , value=0)
radiobutton_real.grid(row=0 , column=2 , padx=2 , pady=2 , sticky="w")

# Select Car Model
label_Evtype = Label(panel_smartcharging , text='Select EV model:')
label_Evtype.grid(row=2 , column=0 , padx=2 , pady=2 , sticky="e")
options_EVtype = [
    "Tata Nexon EV" ,
    "Tesla Model 3" ,
    "Hyundai Ioniq Electric" ,
    "BMW i3 BEV" ,
    "Chevrolet Bolt EV" ,
    "MG ZS EV"
]

optionmenu_EVtype = OptionMenu(panel_smartcharging , variable_EVtype_smart_charging , options_EVtype[1] ,
                               *options_EVtype)
optionmenu_EVtype.grid(row=2 , column=1 , padx=2 , pady=2 , sticky="w")

# inputs provided by user for fast charging
label_initialSoC = Label(panel_smartcharging , text='Initial SoC( in %):')
label_initialSoC.grid(row=3 , column=0 , padx=2 , pady=2 , sticky="e")
entry_nitialSoC = Entry(panel_smartcharging , textvariable=variable_initialSoC_smart_charging)
entry_nitialSoC.grid(row=3 , column=1 , padx=2 , pady=2 , sticky=SW)

label_finalSoC = Label(panel_smartcharging , text='Requested kms:')
label_finalSoC.grid(row=4 , column=0 , padx=2 , pady=2 , sticky=E)
entry_finalSoC = Entry(panel_smartcharging , textvariable=variable_finalSoC_smart_charging)
entry_finalSoC.grid(row=4 , column=1 , padx=2 , pady=2 , sticky=SW)

label_arrival_time = Label(panel_smartcharging , text='Request a Time Slot for Prescheduling:')
label_arrival_time.grid(row=5 , column=0 , padx=2 , pady=2 , sticky=E)

options_timeslot = [
    "12 AM to 3 AM" ,
    "3 AM to 6 AM" ,
    "6 AM to 9 AM" ,
    "9 AM to 12 PM" ,
    "12 PM to 3 PM" ,
    "3 PM to 6 PM" ,
    "6 PM to 9 PM" ,
    "9 PM to 12 AM"

]
optionmenu_timeslot = OptionMenu(panel_smartcharging , variable_timeslot , options_timeslot[2] , *options_timeslot)
optionmenu_timeslot.grid(row=5 , column=1 , padx=2 , pady=2 , sticky="w")

label_requestedtime = Label(panel_smartcharging , text='Tentative departure time(min):')
label_requestedtime.grid(row=6 , column=0 , padx=2 , pady=2 , sticky=E)
entry_requestedtime = Entry(panel_smartcharging , textvariable=variable_requestedtime_smart_charging)
entry_requestedtime.grid(row=6 , column=1 , padx=2 , pady=2 , sticky=SW)

button_schedule = Button(panel_smartcharging , text="Schedule" , command=lambda : Schedule())
button_schedule.grid(row=7 , column=0 , padx=2 , pady=2 , sticky=EW)

button_schedule = Button(panel_smartcharging , text="Insert Data" , command=lambda : Insert_into_users())
button_schedule.grid(row=7 , column=1 , padx=2 , pady=2 , sticky=EW)

button_schedule = Button(panel_smartcharging , text="Assign Current" , command=lambda : current_assignment())
button_schedule.grid(row=7 , column=2 , padx=2 , pady=2 , sticky=EW)

mainloop()
