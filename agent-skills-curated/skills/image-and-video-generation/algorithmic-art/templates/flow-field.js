// Flow Field — Perlin noise vectors (p5.js)
// Open in browser or paste into https://editor.p5js.org

let inc = 0.005;
let scl = 20;
let cols, rows;
let zoff = 0;
let particles = [];
let flowfield;

function setup() {
  createCanvas(800, 800);
  cols = floor(width / scl);
  rows = floor(height / scl);
  flowfield = new Array(cols * rows);
  for (let i = 0; i < 500; i++) particles.push(new Particle());
  background(0);
}

function draw() {
  let yoff = 0;
  for (let y = 0; y < rows; y++) {
    let xoff = 0;
    for (let x = 0; x < cols; x++) {
      let index = x + y * cols;
      let angle = noise(xoff, yoff, zoff) * TWO_PI * 4;
      let v = p5.Vector.fromAngle(angle);
      v.setMag(1);
      flowfield[index] = v;
      xoff += inc;
    }
    yoff += inc;
  }
  zoff += 0.0003;
  for (let p of particles) { p.follow(flowfield); p.update(); p.edges(); p.show(); }
}

class Particle {
  constructor() { this.pos = createVector(random(width), random(height)); this.vel = createVector(0, 0); this.acc = createVector(0, 0); this.maxspeed = 4; this.prev = this.pos.copy(); this.col = color(random(180, 255), random(80, 160), random(180, 255), 80); }
  follow(f) { let x = floor(this.pos.x / scl); let y = floor(this.pos.y / scl); let index = x + y * cols; let force = f[index]; this.acc.add(force); }
  update() { this.vel.add(this.acc); this.vel.limit(this.maxspeed); this.prev = this.pos.copy(); this.pos.add(this.vel); this.acc.mult(0); }
  show() { stroke(this.col); strokeWeight(1); line(this.pos.x, this.pos.y, this.prev.x, this.prev.y); }
  edges() { if (this.pos.x > width || this.pos.x < 0 || this.pos.y > height || this.pos.y < 0) { this.pos = createVector(random(width), random(height)); this.prev = this.pos.copy(); } }
}
