import requests,json,re,calendar,time,cloudscraper,random,aiohttp,asyncio,httpx,random,threading,os
import urllib3
from urllib3.exceptions import InsecureRequestWarning 
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from termcolor import colored
from threading import Thread, Lock
from colorama import Fore, Style, init
from datetime import datetime
import os
from os import sys,path
from dhooks import Webhook, Embed
from autosolveclient import AutoSolve
import webbrowser
from bs4 import BeautifulSoup
import urllib.parse
from tasks import LoadTasks as TaskManager
import paymentSupportASYNC as paymentSupport
import threeDsSupportASYNC as threeDsSupport
from captchaASYNC import Geetest,CapMonsterV2,TwoCaptcha_reCapV2
from captcha_harvester import captchaMain
LOCK = asyncio.Lock()
dirPath = os.environ["DIRPATH"] + "/Footlocker/"

CARTED = 0
CHECKED_OUT = 0
CAPTCHAS_NEEDED = 0 
async def updateStatusBar(updateValue):
    global CARTED
    global CHECKED_OUT
    global CAPTCHAS_NEEDED

    if "cart" in updateValue.lower():
        CARTED += 1
    elif "newcap" in updateValue.lower():
        CAPTCHAS_NEEDED +=1
    elif "removecaptcha" in updateValue.lower():
        CAPTCHAS_NEEDED -=1
    else:
        CHECKED_OUT += 1

    os.system(f"title ZonosLabs - Footlocker / Carted: {str(CARTED)} - Checked Out: {str(CHECKED_OUT)} / Tasks Awaiting Captcha : {str(CAPTCHAS_NEEDED)}")
class Footlocker():

    def __init__(self,task,proxies,i):
        self.task = task
        self.proxies =  proxies
        


        self.pid = self.task["Pid"]
        self.size = self.task["Size"]
        self.payMethod = self.task["PayMethod"]
        self.bypass = bool(self.task["Bypass"])
        self.delay =  float(task["Delay"])
        self.currency ="€"
        self.capAttempts = 0
        self.reCapSitekey = "6LccSjEUAAAAANCPhaM2c-WiRxCZ5CzsjR_vd8uX"
        

        self.taskId = f"Footlocker-Task-{i}"
        if self.task["Profile"]["countryCode"].lower().strip() == "gb":
            self.mainUrl = "https://www.footlocker.co.uk/"
            self.appendUrl = "INTERSHOP/web/FLE/Footlocker-Footlocker_GB-Site/en_GB/-/GBP/"
            self.currency = "£"
        elif self.task["Profile"]["countryCode"].lower().strip() == "de":
            self.mainUrl = "https://www.footlocker.de/"
            self.appendUrl ="INTERSHOP/web/FLE/Footlocker-Footlocker_DE-Site/en_GB/-/EUR/"
        elif self.task["Profile"]["countryCode"].lower().strip() =="fr":
            self.mainUrl ="https://www.footlocker.fr/"
            self.appendUrl = "INTERSHOP/web/FLE/Footlocker-Footlocker_FR-Site/en_GB/-/EUR/"
        elif self.task["Profile"]["countryCode"].lower().strip() == "nl":
            self.mainUrl = "https://www.footlocker.nl/"
            self.appendUrl = "INTERSHOP/web/FLE/Footlocker-Footlocker_NL-Site/en_GB/-/EUR/"
        elif self.task["Profile"]["countryCode"].lower().strip() == "es":
            self.mainUrl = "https://www.footlocker.es/"
            self.appendUrl ="INTERSHOP/web/FLE/Footlocker-Footlocker_ES-Site/en_GB/-/EUR/"
        elif self.task["Profile"]["countryCode"].lower().strip() == "nz":
            self.mainUrl = "https://www.footlocker.co.nz/"
            self.appendUrl = "/INTERSHOP/web/WFS/FootlockerAustraliaPacific-Footlocker_NZ-Site/en_GB/-/NZD/"
        else:
            print(f'Region {self.task["Profile"]["countryCode"].lower().strip()} is unsupported')
            return

        self.addressheaders = {
                'authority': self.mainUrl.replace("https://",''),
                'cache-control': 'max-age=0',
                'upgrade-insecure-requests': '1',
                'origin': self.mainUrl,
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-user': '?1',
                'sec-fetch-dest': 'document',
                'referer': 'https://www.footlocker.co.uk/INTERSHOP/web/FLE/Footlocker-Footlocker_GB-Site/en_GB/-/GBP/ViewCheckoutOverview-Dispatch',
                'accept-language': 'en-US,en;q=0.9',
                }

        
    

    async def tasks(self):
        await self.build_proxy()
        async with httpx.AsyncClient(proxies=self.proxy,timeout=None) as self.session:
            await self.scrape()
            await self.atc()
            await self.getCheckout()
            await self.submitShipping()
            await self.submit_payment()
    
    async def error(self, text):
        spaces = 3 - len(self.taskId)
        MESSAGE = '[{}] [{}{}] {}'.format(Fore.CYAN + datetime.now().strftime('%H:%M:%S.%f') + Style.RESET_ALL, ' ' * spaces, Fore.RED + self.taskId + Style.RESET_ALL, Fore.RED + text)
        async with LOCK:
            print(MESSAGE, Style.RESET_ALL)   

    async def success(self, text):
        spaces = 3 - len(self.taskId)
        MESSAGE = '[{}] [{}{}] {}'.format(Fore.CYAN + datetime.now().strftime('%H:%M:%S.%f') + Style.RESET_ALL, ' ' * spaces, Fore.GREEN + self.taskId + Style.RESET_ALL, Fore.GREEN + text)
        async with LOCK:
            print(MESSAGE, Style.RESET_ALL)
        
    async def warn(self, text):
        spaces = 3 - len(self.taskId)
        MESSAGE = '[{}] [{}{}] {}'.format(Fore.CYAN + datetime.now().strftime('%H:%M:%S.%f') + Style.RESET_ALL, ' ' * spaces, Fore.YELLOW + self.taskId + Style.RESET_ALL, Fore.YELLOW + text)
        async with LOCK:
            print(MESSAGE, Style.RESET_ALL)

    async def info(self, text):
        spaces = 3 - len(self.taskId)
        MESSAGE = '[{}] [{}{}] {}'.format(Fore.CYAN + datetime.now().strftime('%H:%M:%S.%f') + Style.RESET_ALL, ' ' * spaces, Fore.MAGENTA + self.taskId + Style.RESET_ALL, Fore.MAGENTA + text)
        async with LOCK:
            print(MESSAGE, Style.RESET_ALL)
        
    async def status(self, text):
        spaces = 3 - len(self.taskId)
        MESSAGE = '[{}] [{}{}] {}'.format(Fore.CYAN + datetime.now().strftime('%H:%M:%S.%f') + Style.RESET_ALL, ' ' * spaces,self.taskId, text)
        async with LOCK:
            print(MESSAGE, Style.RESET_ALL)
    
    
    

    async def cc_format(self):
        try:
            self.cc = self.task["Profile"]["cardNumber"]
            self.formattedCC = self.cc[:4]+" "+self.cc[4:8]+" "+self.cc[8:12]+" "+self.cc[12:]
            return self.formattedCC
        except:
            await self.error("Error formatting CC data")
            return


    
    async def build_proxy(self):
        self.proxy = None
        if self.proxies == [] or not self.proxies:
            return None
        self.px = random.choice(self.proxies)
        self.splitted = self.px.split(':')
        if len(self.splitted) == 2:
            self.proxy = 'http://{}'.format(self.px)
            return None
        
        elif len(self.splitted) == 4:
            self.proxy = 'http://{}:{}@{}:{}'.format(self.splitted[2], self.splitted[3], self.splitted[0], self.splitted[1])
            return None
        else:
            await self.error('Invalid proxy: "{}", rotating'.format(self.px))
            return None
    
    def sendToDiscord(self, elapsedTime="/", manualCheckout=False, isSuccess=True,threeds=False):
        try:
            self.whSize = self.size["size"]
        except:
            self.whSize = "?"
        #await self.postSuccess(isSuccess=True)
        hook = Webhook(self.task["Profile"]["discordWebhook"])

        if threeds == True: 
            embed = Embed(
                description='',
                color=15105570,
                timestamp='now',
                title="Please confirm your online payment"
            )
            hook = Webhook(self.task["Profile"]["discordWebhook"])

            embed.set_author(name="ZonosLabs", icon_url='https://pbs.twimg.com/profile_images/1257034100478705669/NB7Ornfp_400x400.jpg')
            embed.add_field(name='Site', value=self.mainUrl, inline=False)
            embed.add_field(name='Product', value=self.prodName, inline=False)
            embed.add_field(name='Price',value=f"{self.currency}{self.prodPrice}",inline=True)
            embed.add_field(name='Size', value=self.whSize, inline=False)
            embed.set_footer(text=f'ZonosLabs - FTL {self.task["Profile"]["countryCode"]}',icon_url='https://pbs.twimg.com/profile_images/1257034100478705669/NB7Ornfp_400x400.jpg')
            embed.set_thumbnail(self.prodImg)
            hook.send(embed=embed)
            return


        if isSuccess == True:
            while True:
                #await self.status("Sending webhook to discord")
                if manualCheckout == True:
                    title = "Payment Url Ready"
                else:
                    title = "Checked out"
                embed = Embed(
                    description='',
                    color=7484927,
                    timestamp='now',
                    title=title
                )

                
                
                embed.set_author(name="ZonosLabs", icon_url='https://pbs.twimg.com/profile_images/1257034100478705669/NB7Ornfp_400x400.jpg')
                embed.add_field(name='Site', value=self.mainUrl, inline=False)
                embed.add_field(name='Product', value= self.prodName, inline=False)
                embed.add_field(name="Size", value=self.whSize,inline=False)
                embed.add_field(name='Price',value=f"{self.currency}{self.prodPrice}",inline=True)
                embed.add_field(name="Profile", value=f'||{self.task["Profile"]["profileName"]}||', inline=False)
                embed.add_field(name="Payment Method", value=self.payMethod, inline=False)

                if manualCheckout == True:
                    embed.add_field(name='Complete Payment', value=f'[Complete payment]({self.continueUrl})', inline = False)
                else:
                    embed.add_field(name='Order Number', value=self.orderNumber, inline = False)


                embed.add_field(name="Checkout Speed", value="|| " + str(elapsedTime) + "||", inline=False)
                embed.set_footer(text=f'ZonosLabs - FTL {self.task["Profile"]["countryCode"]}',icon_url='https://pbs.twimg.com/profile_images/1257034100478705669/NB7Ornfp_400x400.jpg')
                embed.set_thumbnail(self.prodImg)

                try:
                    hook.send(embed=embed)

                    spaces = 3 - len(self.taskId)
                    MESSAGE = '[{}] [{}{}] {}'.format(Fore.CYAN + datetime.now().strftime('%H:%M:%S.%f') + Style.RESET_ALL, ' ' * spaces, Fore.GREEN + self.taskId + Style.RESET_ALL, Fore.GREEN + "Sent to discord")
                    print(MESSAGE)
                    self.postSuccess(True)
                    break
                except Exception as e:
                    #await self.error("Couldn't send to discord.")
                    continue
        else:
            embed = Embed(
                description='',
                color=16724787,
                timestamp='now',
                title="Card Decline"
            )

            embed.set_author(name="ZonosLabs", icon_url='https://pbs.twimg.com/profile_images/1257034100478705669/NB7Ornfp_400x400.jpg')
            embed.add_field(name='Site', value=self.mainUrl, inline=False)
            embed.add_field(name="Payment Method", value=self.payMethod, inline=False)
            embed.add_field(name='Product', value=self.prodName, inline=False)
            embed.add_field(name='Price',value=f"{self.currency}{self.prodPrice}",inline=True)
            embed.add_field(name='Size', value=self.size["size"], inline=False)

            embed.set_footer(text=f'ZonosLabs - FTL {self.task["Profile"]["countryCode"]}',icon_url='https://pbs.twimg.com/profile_images/1257034100478705669/NB7Ornfp_400x400.jpg')
            embed.set_thumbnail(self.prodImg)

            try:
                hook.send(embed=embed)
            except Exception as e:
                pass

    async def genKey(self):
       # no sir :)
       return

    async def getCapToken(self, gt, challenge):
        # :(
        return
    
    async def solveCaptchaChallenge(self, captchaUrl):
        #gotta solve datadome yourself sorry
        return
    
    async def get_release_time(self,releaseText) -> int:

        try:
            releaseSplit = releaseText.split("from")

            releaseDay = int(releaseSplit[1].split("/")[0])
            releaseMonth = int(releaseSplit[1].split("/")[1])
            releaseYear = int(releaseSplit[1].split("/")[2].split(" ")[0])


            releaseHour = int(releaseSplit[1].split("21 ")[1].split(":")[0])
            releaseMins = int(releaseSplit[1].split("21 ")[1].split(":")[1])

            releaseDT = datetime(2000+releaseYear, releaseMonth, releaseDay, releaseHour, releaseMins)-datetime.now()

            if self.task["Profile"]["countryCode"].lower() == "gb":
                return int(releaseDT.total_seconds()-10-3600)

            return int(releaseDT.total_seconds()-10)
        except:
            await self.error("Error configurating timer")

            return 0




    async def scrape(self):

        self.startTime = time.time()
        self.timer = False


        while True:
            instock = []
            
            await self.status("Getting product")

            url = self.mainUrl+self.appendUrl+f"ViewProduct-ProductVariationSelect?BaseSKU={self.pid}&InventoryServerity=ProductDetail"

            payload={}
            headers = {
            'authority': self.mainUrl.replace("https://",''),
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://www.footlocker.co.uk/en/p/adidas-hardcourt-pre-school-shoes-4066?v=316475080004',
            'accept-language': 'en-US,en;q=0.9',
            }
            
            try:
                response = await self.session.get(url, headers=headers)
            except Exception as e:
                await self.error(f"Error getting product - {e}")
                await asyncio.sleep(self.delay)
                continue

            if response.status_code == 503:
                await self.warn("Getting product - Waiting in queue")
                await asyncio.sleep(self.delay)
                continue
            elif response.status_code == 403:
                if "geo.captcha-delivery" in response.text:
                    await self.info("Captcha challenge found - Solving")
                    await self.solveCaptchaChallenge(response.json()["url"])
                    continue
                else:
                    await self.error("Getting product - Proxy banned")
                    await asyncio.sleep(self.delay)
                    continue
            elif response.status_code != 200:
                await self.error(f"Error getting product -{response.status_code}")
                await asyncio.sleep(self.delay)
                continue
            else:


                try:
                    stocksoup = BeautifulSoup(response.json()["content"],"html.parser")
                except:
                    await self.error("Error loading sizes")
                    await asyncio.sleep(self.delay)
                    continue

                try:
                    sizes= stocksoup.find("div",{"data-ajaxcontent":f"product-variation-{self.pid}"})
                except:
                    await self.error("Error loading sizes")
                    await asyncio.sleep(self.delay)
                    continue

                try:
                    productJson = json.loads(sizes["data-product-variation-info-json"])
                except:
                    await self.error("Error loading stock")
                    await asyncio.sleep(self.delay)
                    continue


                for item in productJson:
                    if productJson[item]["inventoryLevel"] != 'RED':

                        instock.append({"size":productJson[item]['sizeValue'],"sku":item,"message":productJson[item]['quantityMessage']})

                
                if self.size.lower() == "random" or self.size.lower() == "any":
                    try:
                        self.size = random.choice(instock)
                    except:
                        await self.error("Product OOS")
                        await asyncio.sleep(self.delay)
                        continue


                    await self.success(f"Found random size: {self.size['size']}")
                    stocksoup.decompose()


                    self.sku = self.size['sku']


                    if "This product will be available" in self.size["message"]:
                        try:
                            await self.info(f"Timer found - Sleeping till {self.size['message'].split('from')[1]} CET")
                        except:
                            await self.info(f"Timer found - Sleeping till release")

                        timeToSleep = await self.get_release_time(self.size["message"])


                        await asyncio.sleep(timeToSleep)
                    return
                else:
                    if len(instock) == 0:
                        await self.error("Product OOS")
                        await asyncio.sleep(self.delay)
                        continue
                    else:
                        for item in instock:
                            if item["size"] == self.size.lower():
                                await self.success(f"Found size: {item['size']}")
                                self.sku = item["sku"]

                                if "This product will be available" in item["message"]:
                                    try:
                                        await self.info(f"Timer found - Sleeping till {item['message'].split('from')[1]} CET")
                                    except:
                                        await self.info(f"Timer found - Sleeping till release")

                                    timeToSleep = await self.get_release_time(item["message"])


                                    await asyncio.sleep(timeToSleep)
                                    return
                                else:
                                    return
                            else:
                                pass
                        
                        await self.error("Desired size not found")
                        await asyncio.sleep(self.delay)
                        continue

    
    async def atc(self):
        while True:
            await self.status("Adding to cart")

            url = self.mainUrl+f"en/addtocart?Ajax=true&Relay42_Category=Category%20Pages&acctab-tabgroup-{self.sku}=null&Quantity_{self.sku}=1&SKU={self.sku}"
            self.atcheaders = {
                'authority': 'www.footlocker.co.uk',
                #'content-length': '0',
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest',
                'origin': 'https://www.footlocker.co.uk',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'referer': 'https://www.footlocker.co.uk/en/all/new/',
                'accept-language': 'en-US,en;q=0.9'
            }
            try:
                if self.bypass:
                    pass
                   # not open sourcing this sorry :wink: 
                else:
                    atc = await self.session.post(url,headers=self.atcheaders,data={})
            except Exception as e:
                await self.error(f"Exception adding to cart - {e}")
                await asyncio.sleep(self.delay)
                continue


            if atc.status_code == 405:
                await self.error("OOS during adding to cart")
                await asyncio.sleep(self.delay)
            elif atc.status_code == 503:
                await self.warn("Add to cart - Waiting in queue")
                await asyncio.sleep(self.delay)
                continue
            elif atc.status_code == 502:
                await self.warn("Add to cart - Bad gateway")
                await asyncio.sleep(self.delay)
                continue
            elif atc.status_code == 403:
                if "geo.captcha-delivery" in atc.text:
                    await self.info("Captcha challenge found - Skipping")
                    await self.tasks()
                    try:
                        self.geetestUrl = atc.json()["url"]
                    except:
                        await self.error("Error loading captcha challenge")
                        await asyncio.sleep(self.delay)
                        continue
                    await self.solveCaptchaChallenge(atc.json()["url"])
                    
                    continue
                else:
                    await self.error("Add to cart - Access Denied")
                    await asyncio.sleep(self.delay)
                    continue
            try:
                if "Quantity: 1" in atc.json()["content"]:

                    try:
                        self.prodName = re.findall(r"\"name\">(.*)</span></a",atc.json()["content"])[0]
                    except:
                        self.prodName = "?"
                    
                    try:
                        self.prodPrice =  re.findall(r"price:\"(.{3,6})",atc.json()["content"])[0].replace('"','').replace(",",'')
                    except:
                        self.prodPrice = "?"
                    self.prodImg = f"https://images.footlocker.com/is/image/FLEU/{self.pid}_01?wid=763&hei=538&fmt=png-alpha"
                    
                    
                    await self.success(f"Successfully added {self.prodName} to cart")
                    

                    try:
                        self.synctoken = re.findall(r"SynchronizerToken=(.*)\" c",atc.json()["content"])[0]
                        await updateStatusBar("cart")
                        return
                    except:
                        await self.error("Error getting sync token")
                        await asyncio.sleep(self.delay)
                        continue
                else:
                    await self.error("Error adding to cart")
                    await asyncio.sleep(self.delay)
                    continue
            except Exception as e:
                if "Sold Out!" in atc.text:
                    await self.error("OOS during adding to cart")
                    await asyncio.sleep(self.delay)
                    continue
                else:
                    await self.error("Error checking ATC response")
                    await asyncio.sleep(self.delay)
                    continue
                
            
    
    async def getCheckout(self):

        while True:
            await self.status("Submitting shipping")

            try:
                self.checkoutReq = await self.session.get(self.mainUrl+"en/checkout-overview",headers=self.atcheaders,params={"SynchronizerToken":self.synctoken})
            except Exception as e:
                await self.error(f"Error submitting shipping - {e}")
                await asyncio.sleep(self.delay)
                continue
            
            if self.checkoutReq.status_code == 503:
                await self.warn("Submitting shipping - Waiting in queue")
                await asyncio.sleep(self.delay)
                continue
            elif self.checkoutReq.status_code == 403:
                    if "geo.captcha-delivery" in self.checkoutReq.text:
                        await self.info("Captcha challenge found - Solving")
                        await self.solveCaptchaChallenge(self.checkoutReq.json()["url"])
                        continue
                    else:
                        await self.error("Submitting shipping - Proxy banned")
                        await asyncio.sleep(self.delay)
                        continue
            
            try:
            
                self.addressID = re.findall(r"AddressID\" value=\"(.*)\">",self.checkoutReq.text)
            except:
                await self.error("Error finding address ID")
                await asyncio.sleep(self.delay)
                continue
            
            try:
                self.addressoup = BeautifulSoup(self.checkoutReq.text,"html.parser")
                self.inps = self.addressoup.find("input",{"name":"shipping_AddressID"})["value"]
                self.shippingMethod = self.addressoup.find("input",{"name":"ShippingMethodUUID"})["value"]
                self.paymentMethod = self.addressoup.find("input",{"name":"PaymentServiceSelection"})["value"]
                self.addressoup.decompose()
                return
            except:
                await self.error("Error loading shipping method")
                await asyncio.sleep(self.delay)
                continue
        
    async def submitShipping(self):
        while True:
            
            self.addressPayload = {
                'SynchronizerToken':self.synctoken,
                'isshippingaddress':'',
                'billing_Title':'common.account.salutation.mr.text',
                'billing_FirstName':self.task["Profile"]["firstName"],
                'billing_LastName':self.task["Profile"]["lastName"],
                'billing_CountryCode':self.task["Profile"]["countryCode"],
                'billing_Address1':self.task["Profile"]["address1"],
                'billing_Address2':self.task["Profile"]["houseNumber"],
                'billing_Address3':'',
                'billing_City':self.task["Profile"]["city"],
                'billing_PostalCode':self.task["Profile"]["zipCode"],
                'billing_PhoneHome':self.task["Profile"]["phoneNumber"],
                'billing_BirthdayRequired':'true',
                'billing_Birthday_Day':random.randint(0,28),
                'billing_Birthday_Month':'09',
                'billing_Birthday_Year':random.randint(1980,2000),
                'email_Email':self.task["Profile"]["email"],
                'billing_ShippingAddressSameAsBilling':'true',
                'isshippingaddress':'',
                'shipping_Title':'common.account.salutation.mr.text',
                'shipping_FirstName':'',
                'shipping_LastName':'',
                'SearchTerm':'',
                'shipping_CountryCode':self.task["Profile"]["countryCode"],
                'shipping_Address1':'',
                'shipping_Address2':'',
                'shipping_Address3':'',
                'shipping_City':'',
                'shipping_PostalCode':'',
                'shipping_PhoneHome':'',
                'shipping_AddressID':self.inps,
                'CheckoutRegisterForm_Password':'',
                'promotionCode':'',
                'PaymentServiceSelection':self.paymentMethod,
                'UserDeviceTypeForPaymentRedirect':'Desktop',
                'UserDeviceFingerprintForPaymentRedirect':'0400bpNfiPCR/AUNf94lis1ztkcE2PjoAb7Onrp/XmcfWoVVgr+Rt2dAZDYKGojTbbj7Ay36XoqtPmZrarmVLZEOWTc5J3xnltE7Kq6IhM8HltvDlnXzDbRRZMFlj8uo417+TgsSA5y2mIubuu3Z6HRE9hlin0SRwPNnzubq2X9bgYByCLTiFZJRNnYpPgQiEVyiFhADfeGQZO28FbUrrO5N6T/KhUgGeNqKfeXqFvOptJO+Zpox7t72lJ5rWHf8IT3dHxcEwcGRtW0FKsOE2W0nBYfkLrbf8N9O6F5Axf1NRO8V1uKgdfXRzjC3o7rRuIcSekqy5WS8hYUoDvlKqcW/vgHzj486sjgyUO+AInpd+UykzlhvKatVjussydRjZjLjFmQWppRl6Bv4pp48B2PR0LUM6Rn3JtHEfF9hXdZ4DRRiwxmZVjl9I4KjbE4psB2jCa8teRstFX9MyPpjzYuuV+VhT2JQxvTdTn3ScfrBfYTEXdgVRPEOufCsMUFwtdRMTBML5lyLQdLaggOpa0LGoZf2Nvd6s/J9TXPaqRkCiIiOh9ltHZfQIggPoVjqnTR6FC6A4XHytZ6BH0kBo9oIFO+wPwB7YcyECNO6eLRhhwXvJkdtP6Fqn1OzLhs8hB1R8+g/mDVDCxHwEBUtnxfjeg1YBVxKV6IQOhnzVq0Iwn1hO1Q2jmVgfOlzR3iofwxfmdcDz5A7zOigKnv4/YmxnSaUGABVKw5X0ikb/3h1d0Im6Fy7sPS5usl67lxZGIxL4CJ/ytKbzo6HH6A+040QPjhDYGOJFVPcAfOPjzqyODJKA+IhyeWtUEuHuH9BhO0tceSZkN6ipsurgecSo06izVzqeMmBCH/i9cmKrLQxcxA5OE2KkOZe/0jXzk77ILZ/eUsQ7RNrLro1kTKIs1496YkpIh3A707lm2e25SQbo1NDUFvV16EUQXjOc2c4lTXcu6828R9GQm6kHLdnyFIQwcv2RovzmXNT1g9RJPeBNicb7yAKVlYU34/VcdsVtZ270iAXyzfkdDO/TDp0UzLYS+KjA5OTNopRQtncHmePC+1SwejOX5dhKGYrsu13rc4RCbryu9G8AaRxi/UgQBHzxwUkaRoD62ZVwSe9CFDuhxJuQOMfq4hrni+j8mF/5UOozfmB6grM+bgkmHq7tHomZ4rvIw6RNXNnGPn8TKnBUDHvJYG7xwNxhh89Kh5fIiEifqYAndlMe7YPWuZJQElAfkMG3/KjX3WASiLPAgLTR9UUUA3pDXHzRR0J0Z3KrDBt6QO53m5a4VI05lyt1veYpHNuv7sghWOEeioIZRnmC0W+ochQziz7ftZJCaKwymxS1wfmZzpno81pjMGt2Ji4mSGrSGaUpu0fBeiOThsX3U+DJWOZa5SNRvKs4+F2GzMQtk1ETQsMnbVXub41RnJ/CpzDA9IA29awSDG+zNqC2yf4WSqI9tA4lpeS9ofGZKxixiM2Zfs95CZpSFWx6MgOLTqUfa24IIo9G9ZpRP6mr15vdj85SYD7f2mcXCExKF3qudq9/CMeeFemwsIxewgslIwD4g2I1pH3VpEcwnKnvd96JIohSaxEpfQW3eHArDh6bUQmpXioIyiqvqL5uvSiXt714Heun8ncDenHvJ3BQptrY6b4WQIsDE7SLnGMeFZgzdnjVu1e6xLrxTfXNkVS//paC/SetO6fvD+HbS3y8soyXKRcCn4M6RnckAoP+2sThqdepbM7oSEhnlM0HoDLw07VOnzh7v+3cYjGZG8GEJZMaDZfythgKtW9kGHjEWSeCW35ZK6pKAuVTIqjNO2se1UVsRGsg8tLMcatCFEVI6FwPpPV0ZSMv/EADkUmOPUGc4k1ncIVP7zjHB6rdTl/xhe/dn9zZezDMheOhQbe8v5J7ST/oSdWzA==',
                'ShippingMethodUUID':self.shippingMethod,
                'termsAndConditions':'on',
                'GDPRDataComplianceRequired':'true',
                'sendOrder':''
            }
            
            try:
                self.addressSubmit = await self.session.post(self.mainUrl+self.appendUrl+"ViewCheckoutOverview-Dispatch",data=self.addressPayload,headers=self.addressheaders)
            except Exception as e:
                await self.error(f"Error submitting shipping - {e}")
                await asyncio.sleep(self.delay)
                continue
            
            if self.addressSubmit.status_code == 503:
                await self.warn("Submitting shipping - Waiting in queue")
                await asyncio.sleep(self.delay)
                continue
            elif self.addressSubmit.status_code == 403:
                if "geo.captcha-delivery" in self.addressSubmit.text:
                    await self.info("Captcha challenge found - Solving")
                    try:
                        capCid = re.findall(r"cid':'(.*)','h",self.addressSubmit.text)[0]

                        self.captchaUrl = f"https://datadome.com/?initialCid={capCid}&hash"
                    except:
                        await self.error("Error getting captcha Url")
                        await asyncio.sleep(self.delay)
                        continue

                    await self.solveCaptchaChallenge(self.captchaUrl)
                    continue
                else:
                    await self.error("Submitting shipping - Proxy banned")
                    await asyncio.sleep(self.delay)
                    continue

            if "BarclaycardSmartpay" in str(self.addressSubmit.url):
                await self.success("Submitted shipping")
                if self.payMethod.lower().strip() == "manual":
                    await self.success(f"Found manual Url: {str(self.addressSubmit.url)}")
                    await updateStatusBar("checkout")
                    self.elapsedTime = str(time.time() - self.startTime)
                    self.continueUrl = await paymentSupport.getShortUrl(self.mainUrl,self.session.cookies.jar,str(self.addressSubmit.url))
                    threading.Thread(target=self.sendToDiscord,args=(self.elapsedTime,True,True,False)).start()
                    while True:
                        await asyncio.sleep(100)
                return
            else:
                await self.error("Failed to submit shipping")
                await asyncio.sleep(self.delay)
                continue
            #print(self.addressSubmit.url)
            #print(self.addressSubmit.text)
    async def submit_payment(self):
        while True:
            try:
                self.adyensoup = BeautifulSoup(self.addressSubmit.text,"html.parser")
            except:
                await self.error("Error loading payment")
                await asyncio.sleep(self.delay)
                continue

            self.ccPayload = {}
            try:
                self.adyeninputs = self.adyensoup.find_all("input")
                for item in self.adyeninputs:
                    self.ccPayload.update({item["name"]:item["value"]})
                
                self.adyensoup.decompose()
            except:
                await self.error("Error loading payment form")
                await asyncio.sleep(self.delay)
                continue


            self.adyenHeaders = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "live.adyen.com",
                "Origin": "https://www.footlocker.co.uk",
                "Referer": "https://www.footlocker.co.uk/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36"
            }
            await self.status("Submitting payment")
            try:
                self.adyenPost = await self.session.post("https://live.adyen.com/hpp/pay.shtml",data=self.ccPayload,headers=self.adyenHeaders)
            except Exception as e:
                await self.error(f"Error submiting payment - {e}")
                await asyncio.sleep(self.delay)
                continue

            
            try:
                self.adyensoup = BeautifulSoup(self.adyenPost.text,"html.parser")
                self.ccPayload = {}
                self.adyeninputs = self.adyensoup.find_all("input")
                for item in self.adyeninputs:
                    try:
                        self.ccPayload.update({item["name"]:item["value"]})
                    except:
                        pass
                
                self.adyensoup.decompose()
            except:
                await self.error("Error loading payment info")
                await asyncio.sleep(self.delay)
                continue
            
            if self.payMethod.lower().strip() == "pp" or self.payMethod.lower().strip() == "paypal":
                self.ccPayload["displayGroup"] = "paypal"
                self.ccPayload["paypal.storeOcDetails"] = 'false'
                try:
                    del self.ccPayload["brandName"]
                except:
                    pass

                try:
                    del self.ccPayload["back"]
                except:
                    pass

                self.ccPayload["brandCode"] = 'paypal'
                self.ccPayload["shopperBehaviorLog"] = {"numberBind":"1","holderNameBind":"1","cvcBind":"1","deactivate":"1","activate":"1"}
                self.ccPayload["dfValue"] = 'ryEGX8eZpJ0030000000000000BTWDfYZVR30089146776cVB94iKzBGA0ghUVGkxk5S16Goh5Mk0045zgp4q8JSa00000qZkTE00000q6IQbnyNfpEC4FlSABmQ:40'
                #print(self.ccPayload)
            else:
                try:
                    del self.ccPayload["brandName"]
                except:
                    pass

                try:
                    del self.ccPayload["pay"]
                    del self.ccPayload["back"]
                except:
                    pass

                self.ccPayload["brandCode"] = 'brandCodeUndef'
                self.ccPayload["displayGroup"] = "card"
                self.ccPayload["card.cardNumber"] = await self.cc_format()
                self.ccPayload["card.cardHolderName"] = self.task["Profile"]["firstName"]
                self.ccPayload["card.cvcCode"] = self.task["Profile"]["cardCVC"]
                self.ccPayload["card.expiryMonth"] = self.task["Profile"]["cardExpireMonth"]
                self.ccPayload["card.expiryYear"] = self.task["Profile"]["cardExpireYear"]
                self.ccPayload["shopperBehaviorLog"] = {"numberBind":"1","holderNameBind":"1","cvcBind":"1","deactivate":"3","activate":"2","numberFieldFocusCount":"2","numberFieldLog":"fo@42,cl@42,cl@261,bl@347,fo@494,Cd@498,KL@499,Cu@500,ch@512,bl@512","numberFieldClickCount":"2","numberFieldBlurCount":"2","numberFieldKeyCount":"2","numberFieldChangeCount":"1","numberFieldEvHa":"total=0","holderNameFieldFocusCount":"1","holderNameFieldLog":"fo@512,cl@512,Sd@522,KL@525,KL@526,Su@526,KL@527,KL@528,Ks@530,Sd@531,Su@534,Kb@535,Kb@536,Kb@538,Kb@539,KL@543,KL@544,KL@545,Ks@548,Sd@549,KL@550,Su@551,KL@551,KL@553,KL@555,KL@556,KL@557,KL@558,KL@559,KU@560,ch@560,bl@560","holderNameFieldClickCount":"1","holderNameFieldKeyCount":"25","holderNameUnkKeysFieldLog":"9@560","holderNameFieldChangeCount":"1","holderNameFieldEvHa":"total=0","holderNameFieldBlurCount":"1","cvcFieldFocusCount":"1","cvcFieldLog":"fo@624,cl@625,KN@653,KN@656,KN@657,ch@672,bl@672","cvcFieldClickCount":"1","cvcFieldKeyCount":"3","cvcFieldChangeCount":"1","cvcFieldEvHa":"total=0","cvcFieldBlurCount":"1"}

            self.ppheaders = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': 'live.adyen.com',
                'Origin': 'https://live.adyen.com',
                'Referer': 'https://live.adyen.com/hpp/pay.shtml',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36'
            }


            if self.payMethod.lower().strip() == "pp" or self.payMethod.lower().strip() == "paypal":
                try:
                    self.ppreq = await self.session.post("https://live.adyen.com/hpp/redirectPayPal.shtml",data=self.ccPayload,headers=self.ppheaders)
                except Exception as e:
                    await self.error(f"Error getting PayPal Url - {e}")
                    await asyncio.sleep(self.delay)
                    continue
                if "paypal" in str(self.ppreq.url):
                    await self.success(f"Found PayPal Url: {str(self.ppreq.url)}")
                    await updateStatusBar("checkout")
                    self.elapsedTime = str(time.time() - self.startTime)
                    self.continueUrl = await paymentSupport.getShortUrl("https://www.footlocker.co.uk/",self.session.cookies.jar,str(self.ppreq.url))
                    threading.Thread(target=self.sendToDiscord,args=(self.elapsedTime,True,True,False)).start()
                    while True:
                        await asyncio.sleep(1000)
                else:
                    await self.error("Error getting PayPal Url")
                    await asyncio.sleep(self.delay)
                    continue
            else:
                try:
                    self.ppreq = await self.session.post("https://live.adyen.com/hpp/completeCard.shtml",data=self.ccPayload,headers=self.ppheaders)
                except Exception as e:
                    await self.error(f"Error submitting payment - {e}")
                    await asyncio.sleep(self.delay)
                    continue
                if '3D-Secure</title>' in self.ppreq.text:
                    await self.info("3DS Found - Processing")
                    self.elapsedTime = str(time.time() - self.startTime)

                    threading.Thread(target=self.sendToDiscord,args=(self.elapsedTime,True,True,True)).start()
                    await self.threeds()
                else:
                    await self.error("Error submitting payment")
                    await asyncio.sleep(self.delay)
                    continue
    
    async def threeds(self):
        while True:
            try:
            
                self.cardPage = BeautifulSoup(self.ppreq.text,"html.parser")
                self.authKey = self.cardPage.find_all("input", {"name": "PaReq"})[0]["value"]
                self.threedsurl = self.cardPage.find("form",{"id":"pageform"})["action"]
                self.MDkey = self.cardPage.find_all("input", {"name": "MD"})[0]["value"]
                self.TermUrl = self.cardPage.find_all("input", {"name": "TermUrl"})[0]["value"]
            except Exception as e:
                await self.error("Failed to parse authentication data.")
                await asyncio.sleep(self.delay)
                continue
            else:
               # solve 3ds yourself :)



                self.auth2payload = {
                    'PaRes': self.parestoken,
                    'MD': self.MDkey
                }

                try:
                    self.authpayment = await self.session.post(self.TermUrl, headers=self.addressheaders,data=self.auth2payload)
                    await self.success("Finalised payment 2/2 - Checking order")
                except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                    await self.error(f"Request exception. ({str(type(e).__name__)})")
                    await asyncio.sleep(self.delay)
                    continue
                except Exception as e:
                    await self.error(f"Unknown request exception ({str(e)})")
                    await self.build_proxy()
                    await asyncio.sleep(self.delay)
                    continue
                else:
                    #print(self.authpayment.text)
                    if "Redirecting" in self.authpayment.text:
                        self.confirm3DS = await self.session.post("https://live.adyen.com/hpp/complete3d.shtml",data=self.auth2payload,headers=self.ppheaders)
                        if "RedirectToHPP" in str(self.confirm3DS.url):
                            await self.error("Card declined")
                            threading.Thread(target=self.sendToDiscord,args=(self.elapsedTime,False,False,False)).start()

                            while True:
                                await asyncio.sleep(1000)
                        else:
                            await self.success("Checked out -  Getting order number")
                            await updateStatusBar("checkout")

                            while True:
                                try:
                                    self.orderNumberReq = await self.session.get(str(self.confirm3DS.url),headers=self.atcheaders)
                                except Exception as e:
                                    await asyncio.sleep(self.delay)
                                    continue
                                    
                                try:
                                    self.orderNumber = re.findall(r"id', '(.*)'\);",self.orderNumberReq.text)[1]
                                except:
                                    self.orderNumber = "?"
                                
                                threading.Thread(target=self.sendToDiscord,args=(self.elapsedTime,False,True,False)).start()


                                while True:
                                    await asyncio.sleep(1000)

    
   

async def main():
    os.system("title Zonos - Footlocker")

    # Load tasks
    taskManager = TaskManager("Footlocker/tasks.csv")
    taskManager.load()
    allTasks = taskManager.returnTasks()


    if len(allTasks) == 0:
        print(colored("No task loaded. Closing...", "red"))
        await asyncio.sleep(10)
        return "noTasks"
    else:
        #Load Proxies
        try:
            PROXIES = open(dirPath + 'proxies.txt', 'r').read().splitlines()
            print(colored(f"Loaded {len(PROXIES)} proxies.", "green"))
        except Exception as e:
            print(colored("Could not load proxies.", "red"))
            await asyncio.sleep(10)
            sys.exit()


        captchaMain.server.addSite(
                site="footlocker",
                siteDomain="c.captcha-delivery.com",
                siteKey="6LccSjEUAAAAANCPhaM2c-WiRxCZ5CzsjR_vd8uX",
                captchaType="recapv2"
            )

        if os.environ["CAPTCHAMETHOD"].lower().strip() == "harvester":
            try:
                webbrowser.open("harvesterurl")
            except Exception as e:
                print("Please open {} to solve captcha's.".format("harvesterurl"))

        tasks = []
        i = 0
        for userTask in allTasks:
            newTask = asyncio.create_task(Footlocker(userTask, PROXIES, i).tasks())
            tasks.append(newTask)
            i += 1
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    main()

        
        
