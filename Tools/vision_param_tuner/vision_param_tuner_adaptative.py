#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_param_tuner_adaptative_lite.py
Compact tuner for small screens.
- Few core sliders.
- Advanced knobs via hotkeys.
- Auto-places windows (small) so you can see everything at once.

Hotkeys:
  s : save overlay + JSON
  m : toggle rescue ON/OFF
  f : toggle extra debug windows (Preprocess/Edges/Mask)
  1/2/3 : lighting presets (dim / normal / bright)
  q/ESC : quit
Advanced (hotkeys only):
  ,/. : Close K -/+
  ;/' : Dilate K -/+
  [/] : Rescue Dilate r -/+
  -/+ : Rescue Max Extra % -/+ (step 0.05)
"""

import os, json, cv2, numpy as np
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE, "base4.png")

# ----------------- Helpers -----------------
def odd(k:int)->int: k=int(k); return k if k%2==1 else k+1
def pct_on(m)->float: return 100.0*float((m>0).sum())/float(m.size)
def gaussian_blur(img, b:int):
    k=max(1,2*int(b)+1); return cv2.GaussianBlur(img,(k,k),0),k
def adaptive_thresh(gray):
    return cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,15,5)
def guided_rescue(gray,canny,max_extra,grad_th,dil_r):
    th=adaptive_thresh(gray)
    gx=cv2.Sobel(gray,cv2.CV_16S,1,0,ksize=3); gy=cv2.Sobel(gray,cv2.CV_16S,0,1,ksize=3)
    mag=cv2.convertScaleAbs(cv2.addWeighted(np.abs(gx),1.0,np.abs(gy),1.0,0))
    k=max(1,2*int(dil_r)+1); kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))
    near=cv2.dilate(canny,kernel)
    import_mask=((th>0)&((near>0)|(mag>=grad_th))).astype('uint8')*255
    base_on=int((canny>0).sum()); extra=int((import_mask>0).sum()); cap=int(base_on*max(0.0,max_extra)) if base_on>0 else 0
    if extra>cap and extra>0:
        ys,xs=np.where(import_mask>0); strengths=mag[ys,xs]; idx=strengths.argsort()[::-1][:cap]
        capped=np.zeros_like(import_mask); 
        if cap>0 and idx.size>0: capped[ys[idx],xs[idx]]=255
        import_mask=capped
    merged=cv2.bitwise_or(canny,import_mask)
    merged=cv2.morphologyEx(merged,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    return merged
def ar_score(ar,lo,hi):
    mid=1.0; span=max(mid-lo,hi-mid); return float(max(0.0,1.0-abs(ar-mid)/max(1e-6,span)))
def shape_features(cnt,W,H,ar_lo,ar_hi):
    area=cv2.contourArea(cnt); per=max(1e-6,cv2.arcLength(cnt,True))
    x,y,w,h=cv2.boundingRect(cnt); hull=cv2.convexHull(cnt); a_h=max(1e-6,cv2.contourArea(hull))
    soli=float(area/a_h) if a_h>0 else 0.0; circ=float(min(1.0,4.0*np.pi*area/(per*per)))
    rect=float(area/max(1,w*h)); ar=w/max(1.0,h); ar_s=ar_score(ar,ar_lo,ar_hi); bbox_ratio=(w*h)/float(W*H)
    return dict(area=area,per=per,bbox=(x,y,w,h),ar=ar,solidity=soli,circular=circ,rect=rect,ar_s=ar_s,bbox_ratio=bbox_ratio,fill=rect)

def sigmoid(x): return 1.0/(1.0+np.exp(-x))
def score_contour(feat,cx_img,cy_img,W,H,fill_target,fill_k,w_area,w_fill,w_soli,w_circ,w_rect,w_ar,center_w,center_sigma):
    x,y,w,h=feat['bbox']; area_norm=feat['area']/float(W*H); cx=x+w/2.0; cy=y+h/2.0
    half_diag=np.hypot(W,H)*0.5; d_center=np.hypot(cx-cx_img,cy-cy_img)/max(1e-6,half_diag)
    center_prior=float(np.exp(- (d_center/max(1e-6,center_sigma))**2))
    fill_term=float(sigmoid(fill_k*(feat['fill']-fill_target)))
    score=(w_area*area_norm+w_soli*feat['solidity']+w_rect*feat['rect']+w_ar*feat['ar_s']+w_circ*feat['circular']+w_fill*fill_term+center_w*center_prior)
    parts=dict(area=area_norm,solidity=feat['solidity'],rect=feat['rect'],ar=feat['ar_s'],circ=feat['circular'],fill_term=fill_term,center_prior=center_prior,d_center=d_center)
    return float(score),parts

# ----------------- UI -----------------
WIN_CTRL="Tuner (Lite)"; WIN_OVER="Overlay"; WIN_PRE="Preprocess"; WIN_ED="Edges"; WIN_MK="Mask"

def add_trackbar(win,name,init,maxv): cv2.createTrackbar(name,win,int(init),int(maxv),lambda x:None)

def place_windows():
    # Compact tiling for 1366x768-ish screens
    cv2.moveWindow(WIN_PRE,10,10); cv2.resizeWindow(WIN_PRE,320,240)
    cv2.moveWindow(WIN_MK,340,10); cv2.resizeWindow(WIN_MK,320,240)
    cv2.moveWindow(WIN_ED,670,10); cv2.resizeWindow(WIN_ED,320,240)
    cv2.moveWindow(WIN_OVER,1000,10); cv2.resizeWindow(WIN_OVER,340,255)
    cv2.moveWindow(WIN_CTRL,10,270); cv2.resizeWindow(WIN_CTRL,1330,420)

def main():
    img=cv2.imread(IMG_PATH)
    if img is None: raise FileNotFoundError("Provide 'base.png' next to this script.")
    gray_full=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    # Windows
    cv2.namedWindow(WIN_CTRL,cv2.WINDOW_NORMAL); cv2.namedWindow(WIN_OVER,cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_PRE,cv2.WINDOW_NORMAL);  cv2.namedWindow(WIN_ED,cv2.WINDOW_NORMAL); cv2.namedWindow(WIN_MK,cv2.WINDOW_NORMAL)
    place_windows()

    # Core sliders only
    add_trackbar(WIN_CTRL,"Resize %",100,100)
    add_trackbar(WIN_CTRL,"Blur",2,20)
    add_trackbar(WIN_CTRL,"Canny T1",65,220)
    add_trackbar(WIN_CTRL,"Life min %",3,40)
    add_trackbar(WIN_CTRL,"Life max %",12,60)
    add_trackbar(WIN_CTRL,"Min Area",300,8000)
    add_trackbar(WIN_CTRL,"AR min x100",40,300)
    add_trackbar(WIN_CTRL,"AR max x100",220,300)
    add_trackbar(WIN_CTRL,"BBox cap %",50,100)
    add_trackbar(WIN_CTRL,"Fill target x100",50,100)
    add_trackbar(WIN_CTRL,"Fill k",6,25)
    add_trackbar(WIN_CTRL,"Close K",7,31)
    add_trackbar(WIN_CTRL,"Dilate K",7,31)

    # Advanced (start values; adjusted via hotkeys)
    rescue_enabled=True; rescue_max_extra=0.25; rescue_grad_th=25; rescue_dilate_r=2
    close_k=7; dil_k=7  # defaults; will be overridden by sliders each frame
    w_area=0.12; w_fill=0.35; w_soli=0.18; w_circ=0.10; w_rect=0.15; w_ar=0.10
    center_w=0.25; center_sigma=0.35
    show_debug=True

    print("Lite controls: s=save | m=toggle rescue | f=toggle debug windows | 1/2/3=lighting presets | q/ESC=quit")
    print("Advanced hotkeys: ,/. Close -/+ | ;/' Dilate -/+ | [/] RescueDil -/+ | -/+ RescueExtra -/+")

    while True:
        scale=max(1,cv2.getTrackbarPos("Resize %",WIN_CTRL))/100.0
        blur=cv2.getTrackbarPos("Blur",WIN_CTRL)
        t1=cv2.getTrackbarPos("Canny T1",WIN_CTRL)
        life_min=cv2.getTrackbarPos("Life min %",WIN_CTRL)
        life_max=cv2.getTrackbarPos("Life max %",WIN_CTRL)

        min_area=cv2.getTrackbarPos("Min Area",WIN_CTRL)
        ar_min=cv2.getTrackbarPos("AR min x100",WIN_CTRL)/100.0
        ar_max=cv2.getTrackbarPos("AR max x100",WIN_CTRL)/100.0
        bbox_cap=cv2.getTrackbarPos("BBox cap %",WIN_CTRL)/100.0
        fill_target=cv2.getTrackbarPos("Fill target x100",WIN_CTRL)/100.0
        fill_k=max(1,cv2.getTrackbarPos("Fill k",WIN_CTRL))
        close_k = odd(cv2.getTrackbarPos("Close K",WIN_CTRL))
        dil_k   = odd(cv2.getTrackbarPos("Dilate K",WIN_CTRL))

        # Preprocess
        resized=cv2.resize(gray_full,(0,0),fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
        color_resized=cv2.resize(img,(resized.shape[1],resized.shape[0]),interpolation=cv2.INTER_AREA)
        blurred,k_used=gaussian_blur(resized,blur)
        if show_debug: cv2.imshow(WIN_PRE,blurred)
        else: cv2.imshow(WIN_PRE,np.zeros_like(blurred))

        # Auto Canny
        Kp,MAX_ITER,T2_RATIO=4.0,25,2.5; t1f=float(t1); canny=None
        for _ in range(MAX_ITER):
            t2=int(np.clip(T2_RATIO*t1f,0,255)); canny=cv2.Canny(blurred,int(max(0,t1f)),int(t2)); life=pct_on(canny)
            if life_min<=life<=life_max: break
            if life<life_min: t1f=max(1.0,t1f-Kp*(life_min-life))
            else: t1f=min(220.,t1f+Kp*(life-life_max))

        edges=canny.copy(); used_rescue=False
        if rescue_enabled and pct_on(canny)<life_min:
            edges=guided_rescue(blurred,canny,rescue_max_extra,rescue_grad_th,rescue_dilate_r); used_rescue=True
        if show_debug: cv2.imshow(WIN_ED,edges)
        else: cv2.imshow(WIN_ED,np.zeros_like(edges))

        # Morph
        mask=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((odd(close_k),odd(close_k)),np.uint8),iterations=1)
        mask=cv2.dilate(mask,np.ones((odd(dil_k),odd(dil_k)),np.uint8),iterations=1)
        if show_debug: cv2.imshow(WIN_MK,mask)
        else: cv2.imshow(WIN_MK,np.zeros_like(mask))

        # Contours + score
        H,W=mask.shape[:2]; cx_img,cy_img=W/2.0,H/2.0
        cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        overlay=color_resized.copy(); best=None; best_s=-1e9; best_parts=None
        for c in cnts:
            if cv2.contourArea(c)<min_area: continue
            feat=shape_features(c,W,H,ar_min,ar_max)
            x,y,w,h=feat['bbox']; ar=feat['ar']
            if not (ar_min<=ar<=ar_max): continue
            if (w*h)/(W*H)>bbox_cap: continue
            sc,parts=score_contour(feat,cx_img,cy_img,W,H,fill_target,float(fill_k),w_area,w_fill,w_soli,w_circ,w_rect,w_ar,center_w,center_sigma)
            if sc>best_s: best,best_s,best_parts=(c,feat),sc,parts

        hud=f"BlurK:{k_used} | T1:{int(t1f)} T2:{int(2.5*t1f)} | life:{pct_on(edges):.1f}% | rescue:{int(used_rescue)} | C:{close_k} D:{dil_k} Rr:{rescue_dilate_r} Rx:{rescue_max_extra:.2f}"
        cv2.putText(overlay,hud,(10,24),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2)
        if best is not None:
            cnt,feat=best; x,y,w,h=feat['bbox']; cv2.rectangle(overlay,(x,y),(x+w,y+h),(0,255,0),2)
            M=cv2.moments(cnt)
            if M['m00']!=0:
                cx=int(M['m10']/M['m00']); cy=int(M['m01']/M['m00']); cv2.circle(overlay,(cx,cy),4,(0,255,0),-1)
            txt=f"fill={feat['fill']:.2f} bbox={(w*h)/(W*H):.2f} sc={best_s:.2f}"
            cv2.putText(overlay,txt,(x,max(20,y-6)),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
            panel=f"A:{best_parts['area']:.2f} F:{best_parts['fill_term']:.2f} S:{feat['solidity']:.2f} R:{feat['rect']:.2f} Ar:{feat['ar_s']:.2f} C:{feat['circular']:.2f} Ctr:{best_parts['center_prior']:.2f}"
            cv2.putText(overlay,panel,(10,H-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,0),2)
        cv2.imshow(WIN_OVER,overlay)

        key=cv2.waitKey(1)&0xFF
        if key in (27,ord('q')): break
        elif key==ord('s'):
            ts=datetime.now().strftime('%Y%m%d_%H%M%S'); out=os.path.join(BASE,'results_tuner_lite'); os.makedirs(out,exist_ok=True)
            cv2.imwrite(os.path.join(out,f'lite_{ts}.png'),overlay)
            params=dict(resize_percent=int(scale*100),blur=int(blur),t1_final=int(t1f),life_min=float(life_min),life_max=float(life_max),
                        rescue_enabled=bool(rescue_enabled),rescue_max_extra=float(rescue_max_extra),rescue_grad_thresh=int(rescue_grad_th),
                        rescue_dilate_r=int(rescue_dilate_r),close_k=int(close_k),dilate_k=int(dil_k),min_area=int(min_area),
                        ar_min=float(ar_min),ar_max=float(ar_max),bbox_cap=float(bbox_cap),fill_target=float(fill_target),fill_k=float(fill_k),
                        weights=dict(area=w_area,fill=w_fill,solidity=w_soli,circular=w_circ,rect=w_rect,ar=w_ar),
                        center=dict(weight=center_w,sigma=center_sigma),used_rescue=bool(used_rescue))
            with open(os.path.join(out,f'lite_{ts}.json'),'w',encoding='utf-8') as f: json.dump(params,f,ensure_ascii=False,indent=2)
            print('Saved params+overlay.')
        elif key==ord('m'):
            rescue_enabled=not rescue_enabled
        elif key==ord('f'):
            show_debug=not show_debug
        elif key==ord('1'):  # dim light preset
            cv2.setTrackbarPos('Blur',WIN_CTRL,3); cv2.setTrackbarPos('Life min %',WIN_CTRL,8); cv2.setTrackbarPos('Life max %',WIN_CTRL,16)
        elif key==ord('2'):  # normal
            cv2.setTrackbarPos('Blur',WIN_CTRL,2); cv2.setTrackbarPos('Life min %',WIN_CTRL,5); cv2.setTrackbarPos('Life max %',WIN_CTRL,12)
        elif key==ord('3'):  # bright/contrast
            cv2.setTrackbarPos('Blur',WIN_CTRL,1); cv2.setTrackbarPos('Life min %',WIN_CTRL,4); cv2.setTrackbarPos('Life max %',WIN_CTRL,10)
        # Advanced nudges
        elif key==ord('z'): close_k=max(1,close_k-1)
        elif key==ord('x'): close_k=min(31,close_k+1)
        elif key==ord('c'): dil_k=max(1,dil_k-1)
        elif key==ord('v'): dil_k=min(31,dil_k+1)
        elif key==ord('b'): rescue_dilate_r=max(0,rescue_dilate_r-1)
        elif key==ord('n'): rescue_dilate_r=min(8,rescue_dilate_r+1)
        elif key==ord('m'): rescue_max_extra=max(0.0,round(rescue_max_extra-0.05,2))
        elif key==ord(','): rescue_max_extra=min(0.8,round(rescue_max_extra+0.05,2))

    cv2.destroyAllWindows()

if __name__=='__main__':
    main()
