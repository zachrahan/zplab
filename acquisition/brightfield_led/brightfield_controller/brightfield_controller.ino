// Copyright 2014 WUSTL ZPLAB
// Erik Hvatum (ice.rikh@gmail.com)

const int analogOutPin = 10;
const int enablePin = 0;

void setup()
{
    pinMode(analogOutPin, OUTPUT);
    pinMode(enablePin, OUTPUT);
    TCCR1B = _BV(CS00); // set the timer that controls pin 10 to use 32khz PWM frequency
    analogWrite(analogOutPin, 0);
    digitalWrite(enablePin, HIGH); // pin is inverted: HIGH disables, LOW enables
    Serial.begin(9600);
}

const String cmd_isOk("isOk");
const String cmd_isOn("isOn");
const String cmd_setOn("on=");
const String cmd_getPower("getPower");
const String cmd_setPower("power=");
const String arg_true("true");
const String arg_false("false");

bool ledOn = false;
int power = 0;

void loop()
{
    if(Serial.available() > 0)
    {
        String cmd;
        cmd.reserve(64);
        bool hasArg=false;
        char arg[64];
        int ci;
        char c;
        // Read command
        for(int n=0; n < 63;)
        {
            ci = Serial.read();
            // Serial.read() returns -1 when no data is waiting in the input buffer
            if(ci == -1) continue;
            c = char(ci);
            if(c == '\n' || c == '\r') break;
            cmd += String(c);
            if(c == '=')
            {
                hasArg=true;
                break;
            }
            ++n;
        }
        // Read argument
        if(hasArg)
        {
            int n;
            for(n=0; n < 63;)
            {
                ci = Serial.read();
                if(ci == -1) continue;
                c = char(ci);
                if(c == '\n' || c == '\r') break;
                arg[n] = c;
                ++n;
            }
            arg[n] = '\0';
        }
        // Handle command
        if(cmd.length() > 0)
        {
            if(cmd == cmd_isOk)
            {
                Serial.println("ok==true");
            }
            else if(cmd == cmd_isOn)
            {
                Serial.println(String("on==") + (ledOn ? arg_true : arg_false));
            }
            else if(cmd == cmd_setOn)
            {
                if(hasArg)
                {
                    String sarg(arg);
                    if(sarg == arg_true)
                    {
                        ledOn = true;
                        digitalWrite(enablePin, LOW); // LOW enables 
                        Serial.println("on<-true");
                    }
                    else if(sarg == arg_false)
                    {
                        ledOn = false;
                        digitalWrite(enablePin, HIGH); // HIGH or tri-state disables 
                        Serial.println("on<-false");
                    }
                    else
                    {
                        Serial.println("Error: Unrecognized value provided for on= argument "
                                       "(must be either \"true\" or \"false\", without quotes).");
                    }
                }
                else
                {
                    Serial.println("Error: No argument provided for on= command.");
                }
            }
            else if(cmd == cmd_getPower)
            {
                Serial.println(String("power==") + String(power));
            }
            else if(cmd == cmd_setPower)
            {
                if(hasArg)
                {
                    char *argn, *argne;
                    bool ok = true;
                    for(argn=arg, argne=arg+64; argn != argne; ++argn)
                    {
                        if(*argn == '\0') break;
                        if(!isdigit(*argn))
                        {
                            ok = false;
                            break;
                        }
                    }
                    if(argn == arg)
                    {
                        Serial.println("Error: Empty argument provided for power= command.");
                    }
                    else if(!ok)
                    {
                        Serial.println("Error: Non-digit character in argument provided for power= command.");
                    }
                    else
                    {
                        int v = atoi(arg);
                        if(v < 0 || v > 255)
                        {
                            Serial.println("Error: Argument for power= command must be in the range [0, 255].");
                        }
                        else
                        {
                            power = v;
                            analogWrite(analogOutPin, power);
                            Serial.println(String("power<-") + String(power));
                        }
                    }
                }
                else
                {
                    Serial.println("Error: No argument provided for power= command.");
                }
            }
            else
            {
                Serial.println("Unknown command.  Valid commands are:\n"
                               "    isOk\n"
                               "    isOn\n"
                               "    on=[true|false]\n"
                               "    getPower\n"
                               "    power=[integer >= 0 and <= 255]\n"
                               "A command must be terminated by either CR (\\r), LF (\\n), or "
                               "CRLF(\\r\\n).  All responses are terminated with CRLF (this very response contains "
                               "multiple LFs, but only one CRLF, which appears at its end).");
            }
        }
    }
}
