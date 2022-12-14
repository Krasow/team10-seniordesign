# tkinter : python3 -m pip install tk
# pynput  : puthon3 -m pip install pynput

from pynput.keyboard import Key, Controller
from tkinter import *
import tkinter
from tkinter import messagebox
import cv2
import pyrealsense2
import numpy as np
import imutils
import time
import lgpio
from realsense_depth import *

#####################################################################################################
#                           Setup GUI and display initial score                                     #
#####################################################################################################

GUI = Tk()
# Initialize global variables for score
scoreBLUE = scoreRED = 0
MAX_SCORE = 6; MIN_SCORE = 0
redTotal = blueTotal = 0
redArray = []; blueArray = []; redArrayPrev = []; blueArrayPrev = []

WINNER = 0

dc = DepthCamera()

laser = 4
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(h, laser)
blueScore = 0; redScore = 0
redInningScore = 0; blueInningScore = 0
redTotal = 0; blueTotal = 0
over = 0
LASER = 0
sinkColor = "none"


def getColor(x, y, image):
    RGB = np.flip(image[y][x])
    if (RGB[0] > RGB[1] and RGB[0] > RGB[2] and RGB[0] > 80):
        return "RED"
    elif (RGB[2] > RGB[0] and RGB[1] < RGB[2] and RGB[2] > 70):
        return "BLUE"
    else:
        return ""

# check if a black square is on the board signifying the inning is over
def endInning(x, y, image):
    RGB = np.flip(image[y][x])
    if (RGB[0] < 50 and RGB[2] < 50 and RGB[2] < 50):
        return 1
    else: return 0


# Create instance of keyboard so we can simulate key presses
keyboard = Controller()

# Setup screen with size and background image
GUI.configure(bg='black')
GUI.title("CORNHOLE SCOREBOARD")
GUI.geometry('800x480')
bg = PhotoImage(file = "scoreboard_background.png")
backgroundImage = Label(GUI, image = bg)
backgroundImage.place(x = 0, y = 0)

# Create the blue player's score label
BLUE_SCORE = IntVar()
BLUE_SCORE.set(scoreBLUE)
BLUE_SCORE_LABEL = Label(GUI, textvariable=BLUE_SCORE, font=("times", 250, 'bold'), bg="blue", justify=CENTER)
BLUE_SCORE_LABEL.pack()
BLUE_SCORE_LABEL.place(relx=0.25, rely=0.5, anchor='center')

# Create the red player's score label
RED_SCORE = IntVar()
RED_SCORE.set(scoreRED)
RED_SCORE_LABEL = Label(GUI, textvariable=RED_SCORE, font=("times", 250, 'bold'), bg="red", justify=CENTER)
RED_SCORE_LABEL.pack()
RED_SCORE_LABEL.place(relx=0.75, rely=0.5, anchor='center')

#####################################################################################################

'''
    * Clear Score
        -> i
    * End Game (Exit)
        -> q
'''
def key_pressed(event):
    global BLUE_SCORE
    global RED_SCORE
    global redTotal
    global blueTotal
    if  event.char == 'i':
        redTotal = 0
        blueTotal = 0
        BLUE_SCORE.set(0)
        RED_SCORE.set(0)
    if event.char == "k":
        RED_SCORE.set(max(min(MAX_SCORE, RED_SCORE.get() + 1), MIN_SCORE))
        redTotal += 1
    if event.char == "l":
        RED_SCORE.set(max(0, RED_SCORE.get() - 1))
        redTotal -= 1
    if event.char == "a":
        BLUE_SCORE.set(max(min(MAX_SCORE, BLUE_SCORE.get() + 1), MIN_SCORE))
        blueTotal += 1
    if event.char == "s":
         BLUE_SCORE.set(max(0, BLUE_SCORE.get() - 1))
         blueTotal -= 1
    
    ############### QUIT ###############
    elif event.char == 'q':
        exit()        

#####################################################################################################

# Event handler for key press
GUI.bind('<Key>', key_pressed)
# Startup in full screen mode
GUI.attributes('-fullscreen', True)
time.sleep(3)
ret, depth_back, color_back = dc.get_frame()
gray_back = cv2.cvtColor(color_back, cv2.COLOR_BGR2GRAY)[:, 140:460]
depth_back_crop = depth_back[:, 140:460]
# Execute Image Processing Algorithm
def ImageProcessing():
    global redTotal, blueTotal
    global redArray, blueArray, redArrayPrev, blueArrayPrev
    global dc, laser, h
    global blueScore, redScore, redTotal, blueTotal
    global redInningScore, blueInningScore
    global over
    global LASER
    global sinkColor
    global MAX_SCORE
    global WINNER
    '''
    if (WINNER == 2):
        exit()
    if (WINNER == 1):
        time.sleep(5)
        if redTotal > blueTotal:
            RED_SCORE.set(1)
            BLUE_SCORE.set(0)
        else:
            RED_SCORE.set(0)
            BLUE_SCORE.set(1)
        time.sleep(3)
        WINNER += 1
    '''
    if WINNER == 2:
        exit()
    if WINNER == 1:
        #RED_SCORE.set(1)
        #BLUE_SCORE.set(0)
        time.sleep(3)
        WINNER = 2
        exit()
    cX = cY = 0
    ret, depth_frame, color_frame = dc.get_frame()
    cropped = color_frame[:, 140:460]
    depth_frame_crop = depth_frame[:, 140:460]  
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    gray = cv2.absdiff(gray, gray_back)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 80, 255, cv2.THRESH_BINARY)[1]

    redArrayPrev = redArray.copy()
    blueArrayPrev = blueArray.copy()
    redArray = []
    blueArray = []

    contoursArr = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contoursArr = imutils.grab_contours(contoursArr)
    depth_normal = np.zeros((450,320))
    sub_depth = cv2.absdiff(depth_frame_crop,depth_back_crop)
    #print(f"{sub_depth[280,140]}")
    for contour in contoursArr:
        # compute the center of the contour
        if (over == 1):
            break
        M = cv2.moments(contour)
        if (cv2.contourArea(contour) > 50 and cv2.contourArea(contour) < 8000):
            cX = int(M["m10"] / M["m00"]) 
            cY = int(M["m01"] / M["m00"])
            # draw the contour and center of the shape on the color_frame
            color = getColor(cX, cY, cropped)
            # check for black square
            over = endInning(cX, cY, cropped)
            
            # update blue and red arrays for each side
            #find subdepth average
            avgd = 0
            sumd = 0
            iterations = 0
            #sub_depth = cv2.absdiff(depth_frame_crop,depth_back_crop)
            #depth_normal = cv2.normalize(sub_depth.copy(),depth_normal,0,255,cv2.NORM_MINMAX)
            #cv2.imshow("noramlized",depth_normal)
            '''for i in range(-5, 5):
                for j in range(-5, 5):
                    if cY + i > 449:
                        #print("g tahn 449\n")
                        break
                    if cX + j > 319:
                        #print(f"{cY}\n")
                        break

                    sumd += sub_depth[cY + i, cX + j]
                    iterations += 1
            if iterations:        return "RED"
                avgd = sumd / iterations          
                '''
            if color == "BLUE":
                cv2.drawContours(cropped, [contour], -1, (0, 255, 0), 2)
                #print(f"{avgd}\n")
                #print(f"iterations = {iterations}\n")
                blueArray.append([cX, cY])
            elif color == "RED":
                cv2.drawContours(cropped, [contour], -1, (0, 255, 0), 2)
                #print(f"iterations = {iterations}\n")  
                #print(f"{avgd}\n")
                redArray.append([cX, cY])
            else:
                pass
    while(len(contoursArr) != 0 and over == 1):
        ret, depth_frame, color_frame = dc.get_frame()
        cropped = color_frame[:, 140:460]
        depth = depth_frame[:, 140:460]  
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        gray = cv2.absdiff(gray, gray_back)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 80, 255, cv2.THRESH_BINARY)[1] 
        contoursArr = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        contoursArr = imutils.grab_contours(contoursArr)
        cv2.drawContours(cropped, [contour], -1, (0, 255, 0), 2) 
        print(f"\n\ntotal score\n\n\t\tred : {redTotal}\n\t\tblue: {blueTotal}\n")

    if (over == 1):
        if (blueScore > redScore):
            blueInningScore = blueScore - redScore
            redInningScore = 0
        elif (redScore > blueScore):
            redInningScore = redScore - blueScore
            blueInningScore = 0
        else:
            redInningScore = blueInningScore = 0
        redTotal += redInningScore
        blueTotal += blueInningScore
        RED_SCORE.set(redTotal)
        BLUE_SCORE.set(blueTotal)

    if (len(contoursArr) == 0 and over == 1):
        over = 0
        redScore = blueScore = 0
        redInningScore = blueInningScore = 0
        redArray = []
        blueArray = []
        redArrayPrev = []
        blueArrayPrev = []
        #exit()

    if (redTotal > MAX_SCORE):
        print("\n\nRED WINS\n\n")
        #RED_SCORE.set(redTotal)
        #BLUE_SCORE.set(blueTotal)
        WINNER = 1
        time.sleep(2)
        RED_SCORE.set(1)
        BLUE_SCORE.set(0)
        #time.sleep(3)
        #exit()
    if (blueTotal > MAX_SCORE):
        print("\n\nBLUE WINS\n\n")
        #BLUE_SCORE.set(blueTotal)
        #RED_SCORE.set(redTotal)
        WINNER = 1
        time.sleep(2)
        RED_SCORE.set(0)
        BLUE_SCORE.set(1)
        #time.sleep(3)
        #exit()

    '''
    Score Handler

    * Loop over redBags & blueBags array and determine if they have changed since last time
    -> If array count increases then increase score using the following logic:
        * Bag count has decreased and light barrier interrupt has been triggered
            * Increase bagColorScore by 3 for x number of bags that have left the array
        * Bag count has decreased and light barrier has not been triggered
            * Decrease bagColorScore by 1 for x number of bags that have left the array
    -> If array count decreases the
        been broken: decrease bagColorScore by x number of bags
        * Light Barrier has been broken: Check difference in each team's bag count and handle using standard logic
    '''



   # if laser is detected
    LASER = 0
    if(lgpio.gpio_read(h, laser)):
        LASER = 1
        print("**********************************************\n")
        #time.sleep(0.05)
        # we need to sample multiple spots within the hole
        # since the bag might not go perfectly in the cente
        '''
        sinkColor = getColor(cX, cY, cropped)

        if (sinkColor == ""):
            sinkColor = getColor(197,396,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(154,359,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(127,396,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(164,426,cropped)
        if (sinkColor == ""):
            print("NO COLOR DETECTED\n")
            #cv2.imshow("no detect",cropped.copy())
            #time.sleep(60)
            exit()
        print(sinkColor)
        '''

        sinkColor = getColor(182,363,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(206,357,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(180,387,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(150,356,cropped)
        if (sinkColor == ""):
            sinkColor = getColor(173,335,cropped)
        if (sinkColor == ""):
            print("NO COLOR DETECTED\n")
            #cv2.imshow("no detect",cropped.copy())
            #time.sleep(60)
            #exit()



        print(f"length = {len(blueArray)}, prev = {len(blueArrayPrev)}")
        #exit()
        time.sleep(1)
        #break



    # update blue score
    if len(blueArray) > len(blueArrayPrev):
        bags = len(blueArray) - len(blueArrayPrev) 
        blueScore += 1*bags 
    elif len(blueArray) < len(blueArrayPrev) and LASER and sinkColor == "BLUE":
        bags = len(blueArrayPrev) - len(blueArray)
        #print("\nsink\n")
        #print(f"bags = {bags}\n")
        blueScore += -1*bags
        blueScore += 3*bags
    elif len(blueArray) == len(blueArrayPrev) and LASER and sinkColor == "BLUE":
        blueScore += 3
    elif len(blueArray) < len(blueArrayPrev) and not LASER:
        bags = len(blueArrayPrev) - len(blueArray)
        blueScore += -1*bags
    else:
        pass

    # update red score
    if len(redArray) > len(redArrayPrev):
        bags = len(redArray) - len(redArrayPrev)
        redScore += 1*bags
    elif len(redArray) < len(redArrayPrev) and LASER and sinkColor == "RED":
        bags = len(redArrayPrev) - len(redArray)
        redScore += -1*bags
        redScore += 3*bags
    elif len(redArray) == len(redArrayPrev) and LASER and sinkColor == "RED":
        redScore += 3
    elif len(redArray) < len(redArrayPrev) and not LASER:
        bags = len(redArrayPrev) - len(redArray)
        redScore += -1*bags
    else:
        pass


    cv2.imshow("Color frame", cropped)
    #print(f'Red: {redScore} L: {len(redArray)}')
    #print(f'Blue: {blueScore} L: {len(blueArray)}')
    #print(f"laser = {LASER}")
    print(f"RED: {redScore}\tBLUE: {blueScore}  ---------->>>>    length curr = {len(redArray)}, length prev = {len(redArrayPrev)}\n") 

    GUI.after(1, ImageProcessing)

GUI.after(1, ImageProcessing)
GUI.mainloop()
