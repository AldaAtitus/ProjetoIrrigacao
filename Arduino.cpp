#include <Servo.h>

#define SENSOR_PIN A0
#define LED_VERDE 2
#define LED_AMARELO 3
#define LED_VERMELHO 4
#define BUZZER 5
#define SERVO_PIN 6

Servo valvula;

int umidadeSolo = 0;
int limiteBaixo = 400;   // ajuste por calibração
int limiteAlto = 700;    // ajuste por calibração

unsigned long ultimoCicloAlerta = 0; // para 2 min entre ciclos
const unsigned long intervaloCiclo = 120000; // 2 min

void setup() {
  Serial.begin(9600);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARELO, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  valvula.attach(SERVO_PIN);
  valvula.write(0); // válvula fechada
}

void acionarBuzzerCiclo() {
  // 3 vezes por 5s, com 2s entre cada beep
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(5000);
    digitalWrite(BUZZER, LOW);
    if (i < 2) delay(2000);
  }
}

void loop() {
  umidadeSolo = analogRead(SENSOR_PIN);

  // envia leitura para Raspberry
  Serial.println(umidadeSolo);

  // reset LEDs
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARELO, LOW);
  digitalWrite(LED_VERMELHO, LOW);

  if (umidadeSolo < limiteBaixo) {
    // baixa
    digitalWrite(LED_AMARELO, HIGH);
    valvula.write(0); // fecha válvula
  } else if (umidadeSolo > limiteAlto) {
    // alta
    digitalWrite(LED_VERMELHO, HIGH);
    valvula.write(90); // abre válvula (simulação)
    // ciclo de alerta a cada 2 min
    unsigned long agora = millis();
    if (agora - ultimoCicloAlerta >= intervaloCiclo) {
      acionarBuzzerCiclo();
      ultimoCicloAlerta = agora;
    }
  } else {
    // ideal
    digitalWrite(LED_VERDE, HIGH);
    valvula.write(0); // ideal, fecha válvula
  }

  delay(500); // leitura responsiva; o intervalo real virá da RPi
}
