# yzqj -- generate MissHo glyphs for every 通用规范汉字表一级 char she did not write (2610), ft ckpt, ref 机, 20 steps.
# Char list embedded (base64 utf-8) because `kernels push` only ships this file. Push: kaggle kernels push -p D:/handwriting-font/kaggle/gen3500 The v1 sheet picked style refs
# by sorted-filename first/mid/last, which landed on punctuation (《 ；); only the 机 row was a
# fair test and pretrained had no fair counterpart. This mounts ckpt_ft/ from the finetune
# kernel's output and regenerates the 60 held-out MissHo chars with three REAL-character refs,
# for both pretrained and fine-tuned weights. Push: kaggle kernels push -p D:/handwriting-font/kaggle/finetune-eval
import os, sys, glob, subprocess, functools

WORK = "/tmp/FontDiffuser"
OUT = "/kaggle/working/outputs"
CELL = 96


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


DS = CKPT_FT = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "heldout_missho.txt" in files:
        DS = root
    if root.endswith("ckpt_ft") and "unet.pth" in files:
        CKPT_FT = root
assert DS, "yzqj-finetune-data not mounted"
assert CKPT_FT, "ckpt_ft not mounted (kernel_sources must list yzqj-fontdiffuser-finetune)"
print("DS =", DS, "| CKPT_FT =", CKPT_FT, flush=True)
os.makedirs(OUT, exist_ok=True)

import torch
assert torch.cuda.is_available(), "no CUDA"
if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown"])
ckpt = f"{WORK}/ckpt"
if not os.path.exists(f"{ckpt}/unet.pth"):
    run(["gdown", "--folder", "https://drive.google.com/drive/folders/12hfuZ9MQvXqcteNuz7JQ2B_mUcTr-5jZ", "-O", ckpt])

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)
import sample  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402



import base64, zipfile, time
import numpy as np
from PIL import ImageFont
todo = list(base64.b64decode("5LiA5LiB5Y6C5LiD5Y2c5Lq65YyV5Yeg5YiB5LqG5YiA5LmD5LqO5LqP5LiL5a+45aSn5LiI5LiH5LiK5bCP5be+5Lme5bed5Lq/5Liq5aSV5LmI5Yu65Li45Lqh5Lir5LmL5bC45bex5bez5byT5a2Q5Y2r5Lmf5YiD5Y+J5byA5LqV5aSp5aSr5peg5LqR5LiQ5omO5Y6F5LiN54qs5q255Yy55beo54mZ5bGv5oiI55Om5puw5pel5Lit6LSd5YaI54mb5q+b5aOs5aSt5LuB5LuG5LuH5biB5LuN5pak54iq5LuO5LuR5Ye25LmP5LuT5rCP5Yu/5qyg5YyA5LmM5Yu+5Yek5Lqi5pa55Li65YaX6K6l5b+D5bC65LiR5be05a2U5Yqe5Lul5YWB6YKT5Yqd5Y+M5bm75pyr5omR5Y2J5omS5omU5Y676Im+5Y+v5bem5Y6J55+z5Y+z5aSv5oiK54Gt6L2n5Lic5YyX5Y2g5Ye45Y2i5Lia5biF5pem55Sz5Y+u5Y+q5Y+t5aSu5YWE5Y+95Y+85Y+r5Y+p5Y+o5Y+55YaJ55q/5Ye55Zua55Sf55+i5LmN56a+5LiY5LuX5LuZ5Lus5LuU5LuW5pal55Oc5LmO5Lib55So55Sp5bCU5LmQ5YyG5YaM5Y2v54qv5Yas6bif6aWl5Li75Yav546E6Zeq5YWw5rGB5rGJ5a6B56m05Y+45bC85byX5byY5Ye66L695aW25aW05Y+s55qu5a2V5Y+R5Zyj5a+555+b57qg5bm85Lid6YKm6L+C5YiR5oiO5omb5a+65omj5omY5bep5Zy+5omp5omr5Zyw6ICz6IqL6IqS6Iqd5py95py05p2D6L+H6Iej5ZCP5Y2P5Y6L5Y6M5oiM5Zyo5pyJ6ICM5Yyg5aS454Gw5q275oiQ5aS55aS36L2o6YKq5bCn6LSe5biI5bCY5bCW5Yqj5b2T5ZCQ5ZCT6Jmr5ZCV5ZCK5ZCD5ZCX5ZCG5bG/5bG55biG5bKC5Yia6IKJ5bm05pyx5Lii5bu36IiM56u56L+B5LmU6L+E5LmS5LmT5LyP6Ie85LyQ5Luy5Lyk5Lym5Y2O5Luw5LyZ5Lyq6Ieq5LyK6KGA5Ly85ZCO6Iif5Lya5p2A5LyB54i35Lye6IKM6IKL5py15p2C5Y2x5pes5pet5YyI5aSa5aOu5Yay5aaG5bqE6KGj5Lql5aaE6Zet6Zev576K5bee5rGX5rGh5rGb5rGd5rGk5b+Z5a6H5a6F6K6z6K626K656K685Yac6K696K+A6YKj6L+F5byb5a2Z6Zi16Zi05aW45aaC5aaH5aaD5aW957695Lmw6amu57qk6amv6amw57qr5beh5a+/5byE6bqm546W546b5oiS5ZCe6L+d6Z+n5om25oqa5Z2b5Z2P5oqg5omw5om85ouS5Z2A5omv5oqE6LSh5rGe5Z2d5pS76LWk5oqY5oqT5omz5oqh5omu5oqi5a2d5Z2O5oqR5oqb5Z2f5Z2R5oqX5oqW5aOz5Z2X5omt5oqK5oql5oqS5Yqr6IqZ6Iqc6IuH6Iq96Iq56Iql6Iqs6IuN6Iqz6Iqm6Iqv5Yqz6Iqt5p2G5p2g5p2c5p2R5p2W5p2P5p2J5ber5p2o55Sr5Yyj5ZC+6LGG6YWJ5Yy76L6w5ZCm6L+Y5bCs5q285p2l6L2p5Y2k6IKW5pex55uv5pe25Yqp6YeM5ZGG5ZCx5ZCg5ZGV5pe35ZGA5ZCo5ZC15Liy5ZGQ5ZCf5ZCp5ZGb5ZC75ZC55ZGc5ZCt5ZCn6YKR5ZC85Zuk5ZCu5bKW5bKX5biQ6LSi6ZKJ54mh5oiR5Lmx56eD5YW15Lyw5L2Q5L2R5L2G5Ly45L2D5L2c5Lyv5Ly25L2j5L2O55qC5Ly65Zux5b275b256L+U5Z2Q6LC35aal5ZCr6YK75bKU6IKd6IKb6IKa6IKY6IKg6b6f55S454uC54q554uI5Yig5b2k5Y2154G45bKb5Yio6aWt6aWu5Ya754q25Lqp5Ya15bqK5bqT5bqH55aX5ZCd6L+Z5Ya35bqQ5byD5Ya26Zew6Zey6Ze35YWR54G254G/54G85byf5rGq5rKQ5rKb5rGw5rKl5rKZ5rG95rKD5rKm5rG55rOb5rKn5rKh5rKq5rKI5rKB5b+n5a6L54mi56m354G+56WA6K+I6K+J572V6K+K6K+R5ZCb5bGB5bC/5bC+6L+f5b+M6ZmG6Zi/6Zi76ZmE5Z2g5aaT5aaZ5aaW5aeK5aao5aaS5b+N5Yqy55+j6bih57qs6amx57qv57qx57qy57qz6amz57q157q557q66am057q95aWJ546p5q2m546w546r5oq55Y2m5Z235Z2v5oui5ouU5Z2q5ouj5Z2m5Z2k5oq85oq95ouQ5ouW6aG25ouG5ouO5oq15ouY5oqx5ouE5Z6D5oum5ouM5oun5ouC5ouZ5oqr5ouo5oqs5ouH5ouX6IyJ5piU6Iub6IyC6Iu56IuX6Iuf6IuR6Iue6IyB6IyE6IyO6IuU6IyF5p6J5p6X5p6d5p6i5p+c5p6a5p6Q5p2/5p2+5p6q5p6r5p2t5p6V5Lin5Y2n5LqL5Yi65p6j6YOB55++55+/56CB5Y6V5aWI5aWU5qyn5q605Z6E5aa76L2w6aG36L2u6L2v5Yiw5Y+U5q2n6b2/5Lqb6JmP6IK+5bCa5pe65piG5Zu95ZOO5ZKV5piM5ZG155WF5ZKZ5piC6L+q5Zu65ZG75ZKS5ZKL5ZKQ5ZKP5ZGi5ZKE5bK45bKp5biW572X5bic5biV5bKt6LSl6LSm6LSp6LSs6LSt6LSu6ZKT6L+t5Z6C54mn5LmW5Yiu56eG5ZKM56eJ5L6N5bKz5L6L5L6g5L6l5L6E5L6m5L6j5L6n5L2p6LSn5L6I5Y2R55qE6L+r54is5Yi56IK05pan54i46KeF5Lmz6LSq6LSr5b+/6IKk6IK66IKi6IK/6IOA5pyL6IKh6IKu6IKq6IKl6IOB5piP6bG85YWU54uQ5b+954uX54ue6aWw6aWx6aWy5Lqs5bqe5bqX5bqZ55af55aZ55aa5YmC5Y2S6YOK5bqa5bqf5YeA55uy5rCT6Ze46Ze55Yi45Y2354Ks54KS54KK54KV54KO54KJ5rKr5rWF5rOE5rK95rK+5rOq5rKu5rK55rOK5rK/5rOh5rOj5rOe5rO75rOM5rOl5rK45rK85rOi5rO85rO95oCU5oCv5oCW5oCV5oCc5oCq5oCh5a2m5a6g5a6h5a6Z5a6Y5biY5a6b6YOO6IKp5oi/6KGs6KGr6K+e6K+h6IKD6Zq25bia5bGJ5Yi35bGI5byn5byl5bym5a2f6ZmL6ZmM5a2k6ZmV6ZmN5Ye95aeR5aeT5aeG6L+i6am+5Y+B6Imw57uF6am26am56am757uK6am857uO6LSv5aWR6LSw5463546y54+K54675q+S5out5oyC5bCB5ou35oux5Z6u5oyO5Z+O5oyf5oyg6LW15oyh5ou95ZOJ5oy65Z6i5ou05ou+5Z6b5Z6r5oyj5oyk5oyW5oyq5ouv5p+Q55Sa6I2G6Iy46Iys6I2Q5be36I2J6Iyn6Iy16I2S6Iyr6I2h6I2k6I2n6IOh6I2r6I2U5Y2X6I2v5qCI5p+R5p6v5p+E5qCL5p+l5p+P5qCF5p+z5p+x5p+/5qCP5p+g5YuD6KaB5p+s5ZK45aiB5q2q56CW5Y6Y56CM56CC5rO156Ca56CN6Z2i6ICQ6ICN54m16bil5q6L5q6D6L206bim6Z+t6JmQ56uW55yB5YmK5bCd5pin55u55piv55u855yo5ZOH5ZOE5ZOR5YaS5pif5pio5ZKn5pit55WP6La06IOD6Jm56Jm+6JqB6JqC5ZK96aqC5YuL5ZOX5ZKx5ZOI5ZOG5ZKs5ZKz5ZKq5ZOq5ZOf54Kt5bOh572a6LSx6LS06LS76aqo5bm96ZKZ6ZKd6ZKe6ZKi6ZKg6ZKl6ZKm6ZKn6ZKp6ZKu5Y2457y455yL55+p5q+h5rCi5oCO54my56eS56eN56u/5L+p6LS35L+P5L+d5L+E5L+Q5L6u5L+t5L+X5L+Y55qH5rOJ6ay85L6156a55L6v55u+5b6K6KGN5b6I5Y+Z5YmR6YCD55uG6IOa6IOn6IOG6IOe6IOW6ISJ6IOO54ut54us54uw54uh54ux54ug6LS45oCo5oCl6aW16aW26JqA6aW66aW85bOm5byv5ZOA5Lqt6L+555au55av55ak5ZKo5ae/5bid6Ze66Ze76Ze96ZiA5beu5aec5Y+b6L+357G95aiE5YmN6YCG5YW55oC754K454OB54Ku54Kr54OC5YmD5rS85rSq5rSS5p+S5rWH5rWK5rSe5rWL5rSX5rS95p+T5rSb5rWP5rWO5rSy5rWR5rSl5oGD5oGS5oGi5oGN5oGs5oGk5oGw5oG85oGo5a6m5a6r5a6q56qD6K+r6K+s5omB6KKE56WW56Wg6K+v6K+x6K+y6K+05Z6m6YCA5pei5bGL5pi85bGP5bGO6Zmh6YCK55yJ6Zmo6Zmp5aiD5ael5aeo5ae75aiH5aea5aic5oCS5p6255uI5oCg55m46Jqk5p+U5Z6S57uR57uV6aqE57uY57ua6aqG57ue6aqH6ICV6ICY6ICX6ICZ6Imz5rOw56em54+g5Yy/6JqV6aG955uP5Yyq5o2e5qC95o2V5Z+C5o2C5oyv6LW26LW355uQ5o2O5o2N5o2P5Z+L5o2J5o2G5o2f6KKB5o2M6YO96YCd5o2h5oyr5o2i5oy95oya5oGQ5o2j5aO25o2F5Z+D5oyo6IC76IC/6IC96IGC6I696I6x6I6y6I6r6I6J6I235pmL5oG26I656I665qGG5qKG5qGC5qGU5qCW5qGj5qGQ5qCq5qGl5qGm5qCT5qGD5qGp5qCh5qC35ZOl6YCX5qCX6LS+6YWM57+F6L6x5ZSH5aSP56C456Cw56C+5aWX5q6K5q6J6L2/6L6D6aG/5q+Z5p+05qGM6JmR5YWa6YCe5pmS55yg5pmT5ZOu5ZSg6bit5pmD5ZO65pmM5YmU5pmV6JqM55WU6Jqj6JqK6Jqq6JqT5ZOo5ZOp5ZyD5ZOt5ZOm6biv5ZSk5ZSB5ZO85ZSn5ZWK5ZSJ5ZSG572i5bOt5bOo5bOw5bO76LS86LS/6LWC6LWD6ZKx6ZKz6ZK76ZK+6ZOB6ZOD6ZOF57y65rCn5rCo54m65LmY5pWM56ek56ef56en56ep56eY56yL5YC65YCa5L+65YC+5YCS5YCY5L+x5YCh5YCZ6LWB5L+v5YCN5YCm6Iet5bCE6Lqs5YCU5b6S5b6Q5q636Iiw6Iix6Iis6IC454i56IiA54ix6LG66LG56aKB6aKC57+B6IOw6ISG6ISC6IO46IOz6ISP6ISQ6IO26IST6YCb54u454u85Y2/6YCi6bi16biz55qx6aW/6aaB5YeM5YeE5oGL5qGo5rWG6KGw6KG36YOt55eH55eF55a+55a555a855ay6ISK57SK5ZSQ55O35YeJ5YmW5peB55Wc576e576U55O25ouz57KJ54Ok54OY54Om54On54Ob54Of54OZ6YCS5rab5rWZ5rad5rWm6YWS5raJ5rah5rWp5raC5rW05rWu5raj5rak5ram5ran5raV5rWq5rW45rao54Or5rap5raM5oKW5oKf5oKE5oKN5oKU5oKv5oKm5a6z5a695a6156qN56qE5a6w6K+46K+65omH6K+96KKc6KKN5Yal5Yak6LCF6LCG5Yml5oGz5Ymn5bGR5byx6Zm156Wf6Zm26Zm36Zmq5aix5aif5oGV5ail5aiY6IO95qGR57ui57uj6aqP55CQ55CJ55CF5o2n5aC15o6q5o+P5o265o6p5o2354SJ5o6J5o226LWm5aCG5Z+g5o6A5o275pWZ5o6P5o6Q5o6g5o6C5o635o6n5o6Y5o666IGG5YuY6IGK5ai26JGX6I+x5YuS6I+y6JCM6JCd6I+M6JCO6I+c6JCE6I+K6I+p6JCN6I+g6JCk5Lm+6JCo6I+H5qKw5b2s5amq5qKX5qKn5qKi5qKF5qOA5qKz5qKv5qG25qKt5pWR5pu56YWd6YWX5Y6i5oia56GF56GV5aWi55uU54i96IGL6KKt5Yy+6Zuq6L6G6aKF6Jma5b2q6ZuA55y25YyZ5pmo552B55yv5oKs5ZWq5ZWm5pmm5ZWE6Led6La+5ZWD6Jqv6JuA6JuH5ZSs57Sv6YSC5oKj5ZWw5ZS+5ZSv5ZWk5ZWl5ZW45bSW5bSO5bSt6YC75bSU5bi35bSp5bSb5am05ZyI6ZOQ6ZOb6ZOd6ZOy55+r56e45qKo54qB56e956e756yo56y856yb56yZ5pWP6KKL5oKg5YG/5YG25YGO5YG35ZSu5YGP6Lqv5YWc6KGF5b6Y5b6Z5b6X6KGU55uY6Ii26Ii56Ii15pac55uS6bi95pWb5oKJ5qyy6ISa6ISW6ISv6LGa6IS454yc54yq54yO54yr5Yew54yW54yb56Wt6aaF6aaG5YeR5YeP5q+r54O55bq26bq75bq155eK55eS55eV5buK5bq46bm/55uX56uf5ZWG5peL6ZiO6ZiQ552A576a55y357KY57KX57KS5Ymq5YW954SK54SV6bi/5reL5rav5re55rig5reR5reM5re35reu5reG5riK5rer5riU5reY5rez5ray5rek5reh5reA5rau5amG5riX5oOF5oOc5oOt5oK85oOn5oOV5oOf5oOK5oOm5oK05oOL5oOo5oOv5a+H5a+F5a+C56qS56qR6LCL6LCN6LCO6LCQ6KKx56W356W46LCT6LCa6LCc6YCu5pWi5bCJ5bGg5by56ZqL5aCV6ZqF6ZqQ5ama5am25amJ6aKH6aKI57uq6aqR57uw57uz57u157u357u457u857u957yA5bei55C055Cz55Ci55C85paR5pu/5o+N5aCq5aGU5pCt5aCw5o+p6LaB6LaL5o+95aCk5o+t5b2t5o+j5o+S5o+q5pCc54Wu5o+05pCA6KOB5pCB5pCT5pCC5pCF5aO55pCU5o+J5qy66JGr5pWj5oO56JGs5Yuf6JGb6JGh6JGx6JKL6JKC6Z+p5pyd6L6c6JG15qOS5qOx5qSw5qSN5qOu54Sa5qSF5qSS5qO15qON5qSO5qOJ5qOa5qOV5qO65qaU5qSt5oOg5oOR6YC857Kf5qOY6YWj6YWl5Y6o5Y6m56Gd56Gr6ZuB5q6W6KOC6ZuE6aKK6Zuz5pqC57+Y6L6I5oKy57Sr5Ye/5pWe5qOg5pm0552Q5pqR5pyA5pmw6byO5Za35Zaz5pm25ZaH5ZaK6YGP5pm+55W06LeL6LeM6Leb6YGX6JuZ6Jub6JyT6JyS6Juk5Zad6bmD5ZaC5ZaY5ZaJ5Za75ZW85Zan5bWM5bmF5bi96LWM6LWO6LWQ6LWU6buR6ZO46ZO66ZSA6ZSB6ZSE6ZSF6ZSI6ZSL6ZSM6ZSQ55Sl5o6w55+t5rCu5q+v5rCv6bmF5Ymp56iN56iA56iO562Q562R562W562b562S562P562L562d5YKy5YKF5aCh54Sm5YKN5YKo55qT55qW57Kk5aWl6KGX5oOp5b6h5b6q6ImH6IiS6YC+55Wq6YeK56a96IWK6IS+6IWL6IWU6IWV6bKB54yp54ys54y+54y05oOr54S26aaI6aaL6Juu5bCx5pWm5paM55eY55ei55eq55eb56ul56uj57+U576h5pmu57Kq5bCK5aWg6YGT6YGC54Sw5riv5rue5rmW5rmY5rij5rik5ri65rm/5ri05rqD5rqF5ruR5rmD5rid5rih5ruL5riy5rqJ5oSk5oWM5oOw5oSV5oSj5oO25oSn5oSJ5oWo5Ymy5a+S5a+T56qc56qd56qW56qX56qY6YGN6ZuH6KOV6KOk6KOZ56aF56aE6LCj6LCk6LCm54qA5bGh57Kl55aP6ZqU6ZqZ6ZqY57Wu5auC5aqa5am/57yF57yG57yJ57yO57yT57yU57yV6aqX6aqa57yY55Gf6bmJ55Ge55Gw55GZ6IKG5pG45aGr5pCP5aGM5pGG5pCs5pGH5pCe5aGY5pGK5paf6JKc6Z206Z226bmK6JOd5aKT6JOs6JOE6JKy6JOJ6JKZ6JK45qS/56aB5qWa5qW35qaE5oOz5qeQ5qaG6LWW6YWq6YWs56KN56KY56KR56KO56Kw56KX56KM5bC06Zu36Zu26Zu+6Zu56L6Q6L6R6L6T6aKR6b6E6Ym0552b5525552m556E552r552h552s5Zec6YSZ5Zem5oSa5pqW55uf5q2H5pqX5pqH55W46Le36Lez6Le66Leq6Lek6Lef6YGj6JyI6JyX6Ju+6JyC6JyV5ZeF5Zeh5ZeT572q572p6JyA5bmM6ZSa6ZSh6ZSj6ZSk6ZSl6ZSv6ZSw55+u56ia56ig6aKT5oSB56235q+B6IiF6byg5YKs5YK76Lqy6a2B6KGZ5b6u5oSI6YGl6IW76IWw6IWl6IWu6IW56IW66bmP6IW+6IW/6bKN54y/54We6ZuP6aaN6aaP6YWx56aA55e55buT55e055ew5buJ6Z2W6Z+16KqK57Ku54WO5aGR5oWI54Wk54WM5ryg5ruH5ruk5rul5ruU5rqq5rqc5ryT5rua5rqi5rqv5ruo5rq25rq657Kx5rup5oWO5aGe5a+e56ql56qf5a+d6KSC6KO46LCs5q6/6L6f6Zqc5aqz5auJ5auM5auB5Y+g57ya57yd57yg57yk5Ym/56Kn55KD6LWY54as5aKZ5aKf5pGn6LWr6KqT5pGY5pGU5pKH5oWV5pqu5pG56JST6JSR6JSh6JSX6JS96JS854aZ6JSa5YWi5qeb5qa05qao5qaV6YGt6YW16YW36YW/6YW456Kf56Kx56Kz56OB6L6W6L6X6ZuM6KOz6aKX556F5aKF5Ze96LiK6Jy76Jyh6J2H6JyY6J2J5Zib5ZiA6LWa6ZS56ZS76ZWA6IiU56iz54aP566V566X566p566r6IiG5YOa5YOn6by76a2E6LKM6Iac6IaK6IaA6bKc55aR5a216aaS6KO55pWy6LGq6IaP6YGu6IWQ55ip55if55im6L6j5b2w56ut5peX57K55q2J5byK54aE54aU54W95r2H5ryG5ryx5ryC5ru05ry+5ryP5oWi5oW35a+o5a+h6Jyc5a+l6LCt6IKH6KSQ6KSq6LCx6Zqn5aup57+g54aK5Yez6aqh57yp5pK15pKV5pKS5pKp6Laf5pKR5pKu5pKs5pOS5aKp5pKe5pKk5pKw6IGq6Z6L6Z6N6JWJ6JWK6JSs5qiq5qe95qix5qmh5qif5qmE5pW36LGM6aOY6YaL6YaH6YaJ56OV56OK56OF56K+6ZyH6ZyE6ZyJ556S5pq0556O5Zi75Zi25Ziy5Zi56Lii6Lip6Liq6J226J206J2g6J2O6J2M6J2X6J2Z5Zi/5Zix5bmi5aKo6ZWH6ZWQ6ZWR6Z2g56i956i76buO56i/56i8566x56+T566t5YO16Lq65YO76ImY6Iad6Iab6bKk6bKr54af5pGp6KSS55iq55ik55ir5Yeb5q+F57OK6YG15oaL5r6O5r2u5r2t6bKo5r6z5r2Y5r6I5r6c5r6E5oaU5oeK5oaO57+p6KSl6LC06bmk5oao5YqI6LGr57yt5pK85pOC5pOF6JW+6Jav6Jab6JaH5pOO6JaE6aKg57+w5Zmp5qmx5qmZ5qmY55Oi6ZyN6ZyO6L6Z5YaA5Zi06Lix6LmE6LmC6J+G6J6D5Zmq6bmm6buU6ZWc6LWe56mG56+h56+356+x5YSS6KGh6Iao6ZuV6bK456Oo55i+55i46L6p57OZ57OW54eD5r+S5r6h5oeS5oa+5oeI56q/5aOB57yw57y05oi05pOm6Z6g6JeP6JeQ5qqs5qqQ5qqA56SB56O36Zyc6Zye556t556n556s556z556p556q5puZ6LmL6J666J+L6J+A5ZqO6LWh56mX6a2P57Cn57CH57mB5b6954i15pym6IeK6bOE55mM6L6r6LWi57Of57Og54el5oem6LGB6IeA6IeC57+86aqk6JeV6Z6t6Jek6KaG55676Lmm5Zqj6ZWw57+76bON6bmw54CR6KWf55Kn5oiz5a296K2m6JiR6Je75pSA5pud6Lmy6Lmt6Lms5beF57C457C/6J+56aKk6Z2h55mj55Oj57656bOW54iG55aG6ayT5aOk6ICA6LqB6KCV5Zq85Zq35beN6bOe6a2U57Ov54GM6K2s6KCi6Zy46Zyy6Zy56LqP6buv6auT6LWj5ZuK6ZW255Ok572Q55+X").decode("utf-8"))
assert len(todo) == 2610, len(todo)
uname = lambda ch: f"U{ord(ch):04X}"
cp = lambda p: int(os.path.basename(p).split("+")[1][1:5], 16)
train_refs = [p for p in sorted(glob.glob(f"{DS}/data/train/TargetImage/MissHo/*.jpg")) if 0x4E00 <= cp(p) <= 0x9FFF]
ref = train_refs[len(train_refs) // 2]
print("todo", len(todo), "ref", chr(cp(ref)), flush=True)

# content images: same recipe as finetune-data ContentImage (reverse-fitted 09-20: size 100, textbbox-centred, 128px)
font = ImageFont.truetype(f"{DS}/NotoSansSC.ttf", 100)
CDIR = "/tmp/content"
os.makedirs(CDIR, exist_ok=True)
def render_content(ch):
    p = f"{CDIR}/{uname(ch)}.png"
    if not os.path.exists(p):
        im = Image.new("L", (128, 128), 255)
        d = ImageDraw.Draw(im)
        l, t, r, b = d.textbbox((0, 0), ch, font=font)
        d.text(((128 - (r - l)) / 2 - l, (128 - (b - t)) / 2 - t), ch, font=font, fill=0)
        assert (np.asarray(im) < 128).any(), f"Noto has no glyph for {ch}"
        im.convert("RGB").save(p)
    return p

sys.argv = ["sample.py", f"--ckpt_dir={CKPT_FT}", "--device=cuda:0",
            "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
            "--guidance_scale=7.5", "--num_inference_steps=20", "--method=multistep"]
a = sample.arg_parse()
a.demo = False; a.save_image = False; a.save_image_dir = "/tmp/fd_cfg"; a.character_input = False
pipe = sample.load_fontdiffuer_pipeline(a)

G = f"{OUT}/glyphs"; S = f"{OUT}/sheets"
os.makedirs(G, exist_ok=True); os.makedirs(S, exist_ok=True)
t0 = time.time(); failed = []
batch = []
for i, ch in enumerate(todo):
    a.style_image_path = ref
    a.content_image_path = render_content(ch)
    img = sample.sampling(a, pipe)
    if img is None:
        failed.append(ch); img = Image.new("RGB", (CELL, CELL), "red")
    img = img.convert("RGB").resize((CELL, CELL))
    img.save(f"{G}/{uname(ch)}.png")
    batch.append((Image.open(a.content_image_path).convert("RGB").resize((CELL, CELL)), img))
    if len(batch) == 100 or i == len(todo) - 1:
        n = len(batch); cols = 20; rows = (n + cols - 1) // cols
        sheet = Image.new("RGB", (CELL * cols, CELL * 2 * rows), "white")
        for j, (c, g) in enumerate(batch):
            x, y = (j % cols) * CELL, (j // cols) * 2 * CELL
            sheet.paste(c, (x, y)); sheet.paste(g, (x, y + CELL))
        d = ImageDraw.Draw(sheet)
        for r in range(rows):
            d.line([(0, r * 2 * CELL), (sheet.width, r * 2 * CELL)], fill="red", width=2)
        sheet.save(f"{S}/sheet_{i // 100:02d}.png")
        batch = []
        print(f"{i + 1}/{len(todo)} done, {(time.time() - t0) / 60:.1f} min, failed {len(failed)}", flush=True)

with zipfile.ZipFile(f"{OUT}/glyphs_missho_gen.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(glob.glob(f"{G}/*.png")):
        z.write(p, os.path.basename(p))
open(f"{OUT}/README.txt", "w", encoding="utf-8").write(
    "MissHo generated glyphs: 通用规范汉字表一级 3500 minus her 890 real = 2610 chars | ft ckpt 3000 steps | ref 机 | 20 steps | 96px\n"
    "failed (red): " + "".join(failed) + "\nchars: " + "".join(todo) + "\n")
print("done", len(todo), "failed", len(failed), f"{(time.time() - t0) / 60:.1f} min", flush=True)
