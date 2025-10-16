# MIT License
#
# Copyright (c) 2021 Eugenio Parodi <ceccopierangiolieugenio AT googlemail DOT com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ['TTkKeyPressView']

from typing import List

from TermTk.TTkCore.TTkTerm.input import TTkInput
from TermTk.TTkCore.TTkTerm.inputkey import TTkKeyEvent, mod2str, key2str
from TermTk.TTkCore.TTkTerm.inputmouse import TTkMouseEvent
from TermTk.TTkCore.helper import TTkHelper
from TermTk.TTkCore.signal import pyTTkSlot
from TermTk.TTkCore.constant import TTkK
from TermTk.TTkCore.propertyanimation import TTkPropertyAnimation, TTkEasingCurve
from TermTk.TTkCore.color import TTkColor
from TermTk.TTkWidgets.widget import TTkWidget

from TermTk.TTkTestWidgets.keypressviewfont import TTkKeyPressViewFont

class TTkKeyPressView(TTkWidget):
    __slots__ = ('_fadeDuration', '_keys', '_anim', '_mousePos')

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        TTkInput.inputEvent.connect(self._processInput)
        self._keys:List[List] = []
        self._fadeDuration = 5
        self._mousePos = None
        self._anim = TTkPropertyAnimation(self, '_pushFade')

    @pyTTkSlot(TTkKeyEvent, TTkMouseEvent)
    def _processInput(self, kevt, mevt):
        if kevt is not None: self._addKey(kevt)
        if mevt is not None: self._addMouse(mevt)

    @pyTTkSlot(TTkKeyEvent)
    def _addKey(self, evt):
        if evt.type == TTkK.Character:
            text = evt.key
        else:
            text = key2str(evt.key).replace("Key_",'')
            if evt.mod:
                m = mod2str(evt.mod).replace("Modifier",'')
                text = f"{m} {text}"
        if self._keys and evt.type == self._keys[-1][2] == TTkK.Character:
             self._keys[-1][1]+=evt.key
             self._keys[-1][0]=1
        else:
            self._keys.append([1,text,evt.type])

        self._mousePos = None
        self._startFade()

    @pyTTkSlot(TTkMouseEvent)
    def _addMouse(self, evt):

        self._mousePos = (evt.x, evt.y)

        if evt.evt == TTkMouseEvent.Move:
            self.update()
            return

        key    = evt.key2str().replace('Button', '')   # "Left", "Right", "Mid", "Wheel"
        action = evt.evt2str()                         # "Press","Release","Drag","Up","Down","Left","Right"

        tap = ""
        if evt.tap==1: tap=" SingleClick "
        if evt.tap==2: tap=" DoubleClick "
        if evt.tap==3: tap=" TripleClick "
        if evt.tap>3:  tap=f" {evt.tap} Clicks "
        text = f"{key} {action}{tap}"

        mod = evt.mod2str()
        if mod != "NoModifier":
            text = f"{mod}+{text}"

        self._keys.append([1,text,0x100])
        self._startFade()

    def _startFade(self):
        self._anim.setDuration(self._fadeDuration)
        self._anim.setStartValue(0)
        self._anim.setEndValue(1)
        self._anim.setEasingCurve(TTkEasingCurve.OutExpo)
        self._anim.start()

    def _pushFade(self, fade: float):
        for k in self._keys:
            k[0] -= fade
        # Apply the main fade to the current key
        if self._keys:
            self._keys[-1][0] = 1-fade
        for i,k in enumerate(self._keys):
            if k[0] <= 0:
                self._keys.pop(i)
        self.update()

    def txt2map(self, txt):
        ret = ["","",""]
        for c in txt:
            m = self.fontMap.get(c,["...",". .","..."])
            ret[0] += m[0]
            ret[1] += m[1]
            ret[2] += m[2]
        return ret

    def paintEvent(self, canvas):

        if self._mousePos is not None:
            x, y = self._mousePos
            x_text = f"X={x:4d}"
            y_text = f"Y={y:4d}"
            canvas.drawText(pos=(0,1), text=x_text, color=TTkColor.BOLD)
            canvas.drawText(pos=(0,2), text=y_text, color=TTkColor.BOLD)

        for alpha,text,_ in self._keys:
            r = int(0xbb*alpha)
            g = int(0xff*alpha)
            b = int(0xff*alpha)
            color = TTkColor.fg(f"#{r<<16|g<<8|b:06x}")
            m = self.txt2map(text)
            canvas.drawText(pos=((self.width()-len(text)*3)//2,0),text=m[0],color=color)
            canvas.drawText(pos=((self.width()-len(text)*3)//2,1),text=m[1],color=color)
            canvas.drawText(pos=((self.width()-len(text)*3)//2,2),text=m[2],color=color)

    fontMap = TTkKeyPressViewFont.bitmap
    # fontMap = TTkKeyPressViewFont.calvin_s
