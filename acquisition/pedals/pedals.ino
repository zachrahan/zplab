// /*
//   Drew Sinha
//   Pincus Lab
// */

// The MIT License (MIT)
// 
// Copyright (c) 2014 WUSTL ZPLAB
// 
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// 
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// 
// Authors: Drew Sinha, Zach Pincus, Erik Hvatum

// 
// enum WaitState
// {
//     Idle,
//     WaitForLow,
//     WaitForHigh
// };
// 

const unsigned int ulong_max = __LONG_MAX__ * 2UL + 1UL;

const String cmd_isOk("isOk");
const String cmd_setOn("on=");
const String cmd_getPower("getPower");
const String cmd_setPower("power=");
const String arg_true("true");
const String arg_false("false");

struct Pedal
{
    const int id;
    const int ledPin;
    const int pedalPin;
    bool initing;
    const int upState;
    int state;
    unsigned long changeTimestamp;
    unsigned long debounceInterval;
};

Pedal pedals[] =
{
    {0, 2, 3, true, HIGH, 0, 0, __ULONG_MAX__},
    {1, 4, 5, true, HIGH, 0, 0, 50}
};

Pedal * const pedalsEnd{pedals + sizeof(pedals) / sizeof(Pedal)};

const int pedalsLen = pedalsEnd - pedals;
// 
// char input[1025] = "12345";
// char* inputIt{input};
// char* inputBack{input + sizeof(input) / sizeof(input[0]) - 1};
// int inputLen;
// 
void setup()
{
    for ( Pedal *pedal{pedals};
          pedal != pedalsEnd;
          ++pedal )
    {
        pinMode(pedal->ledPin, OUTPUT);
        pinMode(pedal->pedalPin, INPUT);
        // Turn on internal pull-up resistor on pedal pin
        digitalWrite(pedal->pedalPin, HIGH);

    }

    Serial.begin(115200);
}

void loop()
{
//     if(Serial.available())
//     {
//         char inChr = Serial.read();
//         if(inChr == '\r' || inChr == '\n')
//         {
//             *inputIt = '\0';
//             processInput();
//             inputLen = inputIt - input;
//             inputIt = input;
//         }
//         else if(inputIt == inputBack)
//         {
//             Serial.print("input buffer overflow\n");
//         }
//         else
//         {
//             *inputIt = inChr;
//             ++inputIt;
//         }
//     }
// 
//     for ( Pedal *pedal{pedals}, *pedalse{pedals + sizeof(pedals) / sizeof(Pedal)};
//           pedal != pedalse;
//           ++pedal )
//     {
//         bool finished{false};
//         switch(pedal->waitState)
//         {
//         case WaitForLow:
//             if(digitalRead(pedal->pedalPin) == LOW) finished = true;
//             break;
//         case WaitForHigh:
//             if(digitalRead(pedal->pedalPin) == HIGH) finished = true;
//             break;
//         default:
//             break;
//         }
//         if(finished)
//         {
//             Serial.print(pedal->id);
//             Serial.print(" done\n");
//             pedal->waitState = Idle;
//             digitalWrite(pedal->ledPin, LOW);
//         }
//     }
}
// 
// void processInput()
// {
//     Serial.print('"');
//     Serial.print(input);
//     Serial.print('"');
//     Serial.print("\r\n");
//     if(inputLen >= 3 && input[0] == 'w')
//     {
//         Serial.println();
//         bool isNum{true};
//         for(char* inputIt{input+2}, *inputEnd{input+inputLen}; inputIt < inputEnd; ++inputIt)
//         {
//             Serial.println();
//             if(!isdigit(*inputIt))
//             {
//                 Serial.println();
//                 isNum = false;
//                 break;
//             }
//         }
//         if(isNum)
//         {
//             Serial.println();
//             int num = atoi(input + 2);
//             Serial.print(num);
//             Serial.println();
//             if(num >= 0 && num < sizeof(pedals) / sizeof(Pedal))
//             {
//                 Serial.println();
//                 bool wait{true};
//                 Pedal* pedal{pedals + num};
//                 switch(input[1])
//                 {
//                 case 'H':
//                     pedal->waitState = WaitForHigh;
//                     break;
//                 case 'L':
//                     pedal->waitState = WaitForLow;
//                     break;
//                 case 'C':
//                     pedal->waitState = ((digitalRead(pedal->pedalPin) == LOW) ? WaitForHigh : WaitForLow);
//                     break;
//                 default:
//                     wait = false;
//                     break;
//                 }
//                 if(wait)
//                 {
//                     Serial.println();
//                     digitalWrite(pedal->ledPin, HIGH);
//                 }
//             }
//         }
//     }
//     else if(inputLen >= 2 && input[0] == 'r')
//     {
//         bool isNum{true};
//         for(char* inputIt{input+1}, *inputEnd{input+inputLen}; inputIt != inputEnd; ++inputIt)
//         {
//             if(!isdigit(*inputIt))
//             {
//                 isNum = false;
//                 break;
//             }
//         }
//         if(isNum)
//         {
//             int num = atoi(input + 1);
//             if(num >= 0 && num < sizeof(pedals) / sizeof(Pedal))
//             {
//                 pedals[num].waitState = Idle;
//                 digitalWrite(pedals[num].ledPin, LOW);
//             }
//         }
//     }
// }
// 


// const int ledPin = 2;
// const int pedalPin =3;
// String input = "";
// boolean waiting = false;
// boolean waitState; // Wait until the input pin matches this state
// 
// void setup() {
//   pinMode(ledPin,OUTPUT);
//   pinMode(pedalPin, INPUT);
//   digitalWrite(pedalPin, HIGH);  //Turn on internal pull-up resistor on pedal pin
// 
//   Serial.begin(9600);
// }
// 
// void loop() {
//   if (Serial.available()) {
//      char inChr = Serial.read();
//      if (inChr == '\n') {
//        processInput();
//        input = "";
//      } else {
//        input += inChr;
//      }
//   }
//    if (waiting) {
//      if (digitalRead(pedalPin) == waitState) {
//        waiting = false;
//        Serial.print("done\n");
//        digitalWrite(ledPin, LOW);
//      }
//    }
// }
// 
// void processInput() {
//   if (input[0] == 'w') {
//     waiting = true;
//     digitalWrite(ledPin, HIGH);
//     if (input[1] == 'H') {
//       waitState = HIGH;
//     } else if (input[1] == 'L') {
//       waitState = LOW;
//     } else if (input[1] == 'C') {
//       waitState = !digitalRead(pedalPin);
//     }
//   } else if (input[0] == 'r') {
//     waiting = false;
//     digitalWrite(ledPin, LOW);
//     Serial.print("reset\n");
//   }
// }
