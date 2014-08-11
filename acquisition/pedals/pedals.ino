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

const unsigned int ulong_max = __LONG_MAX__ * 2UL + 1UL;

struct Pedal
{
    // Note: member variables are in descending order of size so that smaller variables can be packed together at the
    // end of the object rather than offsetting larger types as the beginning that must be aligned on multibyte
    // boundries; eg a char preceeding a quad byte type would cause three bytes to be wasted for alignment of the
    // quad.
    unsigned long changeTimestamp;
    unsigned long debounceInterval;
    const int id;
    const int ledPin;
    const int pedalPin;
    int downState;
    bool initing;
    // True if the last update transmitted for this Pedal indicated that the Pedal was down
    bool downAtLastUpdate;

    constexpr Pedal(const int id_,
                    const int ledPin_,
                    const int pedalPin_,
                    int downState_,
                    unsigned long debounceInterval_)
      : changeTimestamp{0UL},
        debounceInterval{debounceInterval_},
        id{id_},
        ledPin{ledPin_},
        pedalPin{pedalPin_},
        downState{downState_},
        initing{true},
        downAtLastUpdate{false}
    {
    }

    inline bool read()
    {
        return digitalRead(pedalPin) == downState;
    }
};

Pedal pedals[] =
{
    Pedal(0, 2, 3, HIGH, 50),
    Pedal(1, 4, 5, HIGH, 50)
};

Pedal * const pedalsEnd{pedals + sizeof(pedals) / sizeof(Pedal)};

const int pedalsLen = pedalsEnd - pedals;

char input[129];
char* inputIt{input};
char* inputLast{input + sizeof(input) / sizeof(input[0]) - 1};

void setup()
{
    for ( Pedal *pedal{pedals};
          pedal != pedalsEnd;
          ++pedal )
    {
        pinMode(pedal->ledPin, OUTPUT);
        digitalWrite(pedal->ledPin, LOW);
        pinMode(pedal->pedalPin, INPUT);
        // Turn on internal pull-up resistor on pedal pin
        digitalWrite(pedal->pedalPin, HIGH);

        pedal->downAtLastUpdate = pedal->read();
        pedal->changeTimestamp = millis();
    }

    Serial.begin(115200);
}

void loop()
{
    updateStateAccordingToPhysicalWorld();
    updateStateAccordingToUser();
}

void updateStateAccordingToPhysicalWorld()
{
    for ( Pedal *pedal{pedals};
          pedal != pedalsEnd;
          ++pedal )
    {
        bool nowDown{pedal->read()};
        const unsigned long timestamp{millis()};

        if(!pedal->initing && nowDown == pedal->downAtLastUpdate)
        {
            pedal->changeTimestamp = 0;
        }
        else
        {
            if(nowDown)
            {
                // Notify the instant of the first switch glitch harkening a sustained downing of at least
                // pedal->debounceInterval milliseconds (anything less will nonetheless result in an up notification
                // being transmitted in pedal->debounceInterval milliseconds).
                Serial.print("pedal ");
                Serial.print(pedal->id);
                Serial.println(" state changed to down");
                digitalWrite(pedal->ledPin, HIGH);
                pedal->downAtLastUpdate = true;
                pedal->initing = false;
            }
            else if(pedal->changeTimestamp == 0)
            {
                // Pedal has gone up.  Start waiting for pedal->debounceInterval milliseconds of continuous upness
                // before building sufficient confidence that it's up and not still in the process of going up.
                pedal->changeTimestamp = timestamp;
            }
            else if(timestamp - pedal->changeTimestamp > pedal->debounceInterval)
            {
                // Pedal upness certified, stored, and user is notified
                Serial.print("pedal ");
                Serial.print(pedal->id);
                Serial.println(" state changed to up");
                digitalWrite(pedal->ledPin, LOW);
                pedal->downAtLastUpdate = false;
                pedal->changeTimestamp = 0;
                pedal->initing = false;
            }
        }
    }
}

void updateStateAccordingToUser()
{
    if(Serial.available())
    {
        int inChrI;
        char inChr;
        for(;;)
        {
            inChrI = Serial.read();
            inChr = static_cast<char>(inChrI);
            if(inChrI == -1)
            {
                // No more data is waiting in serial rx buffer
                break;
            }
            else if(inChr == '\r' || inChr == '\n')
            {
                // Chop off trailing whitespace
                --inputIt;
                for(; inputIt >= input && (*inputIt == ' ' || *inputIt == '\t'); --inputIt);
                ++inputIt;

                *inputIt = '\0';
                processInput();
                inputIt = input;
            }
            else
            {
                *inputIt = inChr;
                ++inputIt;
                if(inputIt == inputLast)
                {
                    // The character received is not a command terminator (a line return of some kind), and yet we are out of
                    // space in our input buffer for anything but the required null terminator
                    Serial.println("*WARNING: The input buffer overflowed and previous contents have been cleared.");
                    inputIt = input;
                    *inputIt = inChr;
                    ++inputIt;
                }
            }
        }
    }
}

bool advanceIfWhitespace()
{
    bool advanced{false};
    for(; *inputIt == ' ' || *inputIt == '\t'; ++inputIt)
    {
        advanced = true;
    }
    return advanced;
}

bool advanceIfStr(const char* str)
{
    bool advanced{false};
    char* ii{inputIt};
    const char* si{str};
    for(;;)
    {
        if(*si == '\0')
        {
            // Reached end of str before end of input with no mismatch; advance input iterator to first element after
            // match
            advanced = true;
            inputIt = ii;
            break;
        }
        if(*ii == '\0')
        {
            // Reached end of input before end of str; no match, do not advance
            break;
        }
        if(*ii != *si)
        {
            // Mismatch
            break;
        }
        ++si;
        ++ii;
    }
    return advanced;
}

bool advanceIfGetPositiveInt(int& pi)
{
    bool advanced{false};
    char *ii{inputIt};
    for(; isdigit(*ii); ++ii);
    if ( ii != inputIt
      && (*ii == ' ' || *ii == '\t' || *ii == '\0') )
    {
        pi = atoi(inputIt);
        advanced = true;
        inputIt = ii;
    }
    return advanced;
}

bool advanceIfGetUnsignedLong(unsigned long& ul)
{
    bool advanced{false};
    char* ii{inputIt};
    for(; isdigit(*ii); ++ii);
    if ( ii != inputIt
      && (*ii == ' ' || *ii == '\t' || *ii == '\0') )
    {
        ul = strtoul(inputIt, nullptr, 10);
        advanced = true;
        inputIt = ii;
    }
    return advanced;
}

void processInput()
{
    inputIt = input;
    advanceIfWhitespace();
    bool ok{false};
    int pedalId;
    if(advanceIfStr("get ok") && *inputIt == '\0')
    {
        Serial.println("ok is true");
        ok = true;
    }
    else if ( advanceIfStr("set")
           && advanceIfWhitespace()
           && advanceIfStr("pedal")
           && advanceIfWhitespace()
           && advanceIfGetPositiveInt(pedalId) && pedalId >= 0 && pedalId < pedalsLen
           && advanceIfWhitespace() )
    {
        Pedal* pedal{pedals + pedalId};
        unsigned long debounceInterval;
        if ( advanceIfStr("debounceInterval")
          && advanceIfWhitespace()
          && advanceIfStr("to")
          && advanceIfWhitespace()
          && advanceIfGetUnsignedLong(debounceInterval)
          && *inputIt == '\0' )
        {
            pedal->debounceInterval = debounceInterval;
            Serial.print("pedal ");
            Serial.print(pedal->id);
            Serial.print(" debounceInterval set to ");
            Serial.println(pedal->debounceInterval);
            ok = true;
        }
        if ( advanceIfStr("downState")
          && advanceIfWhitespace()
          && advanceIfStr("to")
          && advanceIfWhitespace() )
        {
            if(advanceIfStr("low") && *inputIt == '\0')
            {
                pedal->downState = LOW;
                ok = true;
            }
            else if(advanceIfStr("high") && *inputIt == '\0')
            {
                pedal->downState = HIGH;
                ok = true;
            }

            if(ok)
            {
                Serial.print("pedal ");
                Serial.print(pedal->id);
                Serial.print(" downState set to ");
                Serial.println(pedal->downState == LOW ? "low" : "high");
            }
        }
    }
    else if ( advanceIfStr("get")
           && advanceIfWhitespace()
           && advanceIfStr("pedal")
           && advanceIfWhitespace()
           && advanceIfGetPositiveInt(pedalId) && pedalId >= 0 && pedalId < pedalsLen
           && advanceIfWhitespace() )
    {
        Pedal* pedal{pedals + pedalId};
        if(advanceIfStr("debounceInterval") && *inputIt == '\0')
        {
            Serial.print("pedal ");
            Serial.print(pedal->id);
            Serial.print(" debounceInterval is ");
            Serial.println(pedal->debounceInterval);
            ok = true;
        }
        else if(advanceIfStr("downState") && *inputIt == '\0')
        {
            Serial.print("pedal ");
            Serial.print(pedal->id);
            Serial.print(" downState is ");
            Serial.println(pedal->downState == LOW ? "low" : "high");
            ok = true;
        }
        else if(advanceIfStr("state") && *inputIt == '\0')
        {
            Serial.print("pedal ");
            Serial.print(pedal->id);
            Serial.print(" state is ");
            Serial.println(pedal->downAtLastUpdate ? "down" : "up");
            ok = true;
        }
    }

    if(!ok)
    {
        Serial.println("*ERROR: Unknown or invalid command.");
        Serial.println("*Valid command are:");

        Serial.println("*    get ok");

        Serial.print("*    set pedal [0, ");
        Serial.print(pedalsLen);
        Serial.println(") debounceInterval to POSITIVE_INTEGER");

        Serial.print("*    get pedal [0, ");
        Serial.print(pedalsLen);
        Serial.println(") debounceInterval");

        Serial.print("*    set pedal [0, ");
        Serial.print(pedalsLen);
        Serial.println(") downState to [low|high]");

        Serial.print("*    get pedal [0, ");
        Serial.print(pedalsLen);
        Serial.println(") downState");

        Serial.print("*    get pedal [0, ");
        Serial.print(pedalsLen);
        Serial.println(") state");

        Serial.println("*Commands are terminated by cr, lf or crlf.  Warning and error replies are prepended with *.");
    }
}
