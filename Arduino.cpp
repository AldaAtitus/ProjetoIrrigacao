#include <Servo.h>

#define SENSOR_PIN A0
#define LED_VERDE 2
#define LED_AMARELO 3
#define LED_VERMELHO 4
#define BUZZER 5
#define SERVO_PIN 6

Servo valvula;

int umidadeSolo = 0;
int limiteBaixo = 400;   // valor inicial (pode ser atualizado via serial)
int limiteAlto = 700;    // valor inicial (pode ser atualizado via serial)
int intervalo = 2;       // segundos, atualizado via serial

unsigned long ultimoCicloAlerta = 0;
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
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(5000);
    digitalWrite(BUZZER, LOW);
    if (i < 2) delay(2000);
  }
}

void loop() {
  // --- Lê comandos vindos da Raspberry ---
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando.startsWith("ALVO:")) {
      limiteAlto = comando.substring(5).toInt();
      Serial.print("Novo limiteAlto: ");
      Serial.println(limiteAlto);
    } else if (comando.startsWith("INTERVALO:")) {
      intervalo = comando.substring(10).toInt();
      Serial.print("Novo intervalo: ");
      Serial.println(intervalo);
    }
  }

  // --- Lê sensor ---
  umidadeSolo = analogRead(SENSOR_PIN);
  Serial.println(umidadeSolo); // envia leitura para Raspberry

  // --- LEDs e válvula ---
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARELO, LOW);
  digitalWrite(LED_VERMELHO, LOW);

  if (umidadeSolo < limiteBaixo) {
    digitalWrite(LED_AMARELO, HIGH);
    valvula.write(0); // fecha válvula
  } else if (umidadeSolo > limiteAlto) {
    digitalWrite(LED_VERMELHO, HIGH);
    valvula.write(90); // abre válvula
    unsigned long agora = millis();
    if (agora - ultimoCicloAlerta >= intervaloCiclo) {
      acionarBuzzerCiclo();
      ultimoCicloAlerta = agora;
    }
  } else {
    digitalWrite(LED_VERDE, HIGH);
    valvula.write(0); // ideal, fecha válvula
  }

  delay(intervalo * 1000); // intervalo controlado pela Raspberry
}