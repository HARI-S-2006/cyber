import { useFrame, useThree } from '@react-three/fiber'
import { useMemo, useRef, useEffect, Suspense } from 'react'
import * as THREE from 'three'
import { useStore } from '../../hooks/useStore'

const EARTH_RADIUS = 50
const ARC_HEIGHT = 20

function latLonToVector3(lat: number, lon: number, radius: number = EARTH_RADIUS): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  )
}

function createArcGeometry(
  start: THREE.Vector3,
  end: THREE.Vector3,
  height: number = ARC_HEIGHT,
  color: THREE.Color = new THREE.Color(0x39FF14)
): THREE.Mesh {
  const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)
  const midLength = mid.length()
  mid.normalize().multiplyScalar(EARTH_RADIUS + height)
  
  const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
  const points = curve.getPoints(32)
  
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.8,
    linewidth: 2,
  })
  
  return new THREE.Line(geometry, material)
}

function ThreatArc({ 
  startLat, startLon, endLat, endLon, 
  color, progress, intensity 
}: {
  startLat: number
  startLon: number
  endLat: number
  endLon: number
  color: THREE.Color
  progress: number
  intensity: number
}) {
  const startRef = useRef<THREE.Vector3>(latLonToVector3(startLat, startLon))
  const endRef = useRef<THREE.Vector3>(latLonToVector3(endLat, endLon))
  const lineRef = useRef<THREE.Line | null>(null)
  const progressRef = useRef(progress)
  
  useEffect(() => {
    progressRef.current = progress
  }, [progress])
  
  useFrame(() => {
    if (!lineRef.current) return
    
    const p = progressRef.current
    if (p <= 0 || p >= 1) return
    
    const start = startRef.current
    const end = endRef.current
    
    const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)
    const midLength = mid.length()
    mid.normalize().multiplyScalar(EARTH_RADIUS + ARC_HEIGHT * intensity)
    
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
    const points = curve.getPoints(32)
    
    const geometry = lineRef.current.geometry as THREE.BufferGeometry
    const positions = geometry.attributes.position.array
    
    for (let i = 0; i <= 32; i++) {
      const t = i / 32
      if (t <= p) {
        positions[i * 3] = points[i].x
        positions[i * 3 + 1] = points[i].y
        positions[i * 3 + 2] = points[i].z
      } else {
        positions[i * 3] = positions[i * 3 + 1] = positions[i * 3 + 2] = 0
      }
    }
    
    geometry.attributes.position.needsUpdate = true
  })
  
  const start = useMemo(() => latLonToVector3(startLat, startLon), [startLat, startLon])
  const end = useMemo(() => latLonToVector3(endLat, endLon), [endLat, endLon])
  const mid = useMemo(() => {
    const m = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)
    m.normalize().multiplyScalar(EARTH_RADIUS + ARC_HEIGHT * intensity)
    return m
  }, [start, end, intensity])
  
  const curve = useMemo(() => new THREE.QuadraticBezierCurve3(start, mid, end), [start, mid, end])
  const points = useMemo(() => curve.getPoints(32), [curve])
  
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry().setFromPoints(points)
    return g
  }, [points])
  
  const material = useMemo(() => new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.7 * intensity,
    linewidth: 2,
  }), [color, intensity])
  
  return (
    <line ref={lineRef} geometry={geometry} material={material} />
  )
}

function ParticleField() {
  const particlesRef = useRef<THREE.Points | null>(null)
  const count = 2000
  
  useEffect(() => {
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    const colors = new Float32Array(count * 3)
    const alphas = new Float32Array(count)
    
    for (let i = 0; i < count; i++) {
      const radius = EARTH_RADIUS + 50 + Math.random() * 100
      const phi = Math.acos(2 * Math.random() - 1)
      const theta = 2 * Math.PI * Math.random()
      
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.cos(phi)
      positions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta)
      
      sizes[i] = Math.random() * 2 + 0.5
      colors[i * 3] = 0
      colors[i * 3 + 1] = 0.8 + Math.random() * 0.2
      colors[i * 3 + 2] = 1
      alphas[i] = Math.random() * 0.5 + 0.1
    }
    
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.setAttribute('alpha', new THREE.BufferAttribute(alphas, 1))
    
    const material = new THREE.PointsMaterial({
      size: 1.5,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      sizeAttenuation: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    
    const particles = new THREE.Points(geometry, material)
    particlesRef.current = particles
    
    return () => {
      geometry.dispose()
      material.dispose()
    }
  }, [])
  
  useFrame(({ clock }) => {
    if (!particlesRef.current) return
    
    const positions = particlesRef.current.geometry.attributes.position.array
    const alphas = particlesRef.current.geometry.attributes.alpha.array
    const time = clock.getElapsedTime()
    
    for (let i = 0; i < count; i++) {
      positions[i * 3 + 1] += Math.sin(time + i) * 0.02
      alphas[i] = 0.1 + Math.sin(time * 2 + i) * 0.05
    }
    
    particlesRef.current.geometry.attributes.position.needsUpdate = true
    particlesRef.current.geometry.attributes.alpha.needsUpdate = true
    particlesRef.current.material.opacity = 0.6
  })
  
  return <points ref={particlesRef} />
}

function Earth() {
  const earthRef = useRef<THREE.Mesh | null>(null)
  const atmosphereRef = useRef<THREE.Mesh | null>(null)
  
  useEffect(() => {
    const loader = new THREE.TextureLoader()
    
    loader.load('/textures/earth_day.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      if (earthRef.current) {
        earthRef.current.material.map = texture
        earthRef.current.material.needsUpdate = true
      }
    })
    
    loader.load('/textures/earth_night.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      if (earthRef.current) {
        earthRef.current.material.emissiveMap = texture
        earthRef.current.material.emissive = new THREE.Color(0x332211)
        earthRef.current.material.emissiveIntensity = 0.5
        earthRef.current.material.needsUpdate = true
      }
    })
    
    loader.load('/textures/earth_specular.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      if (earthRef.current) {
        earthRef.current.material.specularMap = texture
        earthRef.current.material.specular = new THREE.Color(0x111133)
        earthRef.current.material.needsUpdate = true
      }
    })
    
    loader.load('/textures/earth_clouds.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      texture.wrapS = THREE.RepeatWrapping
      texture.wrapT = THREE.RepeatWrapping
      
      const cloudMesh = new THREE.Mesh(
        new THREE.SphereGeometry(EARTH_RADIUS + 2, 64, 64),
        new THREE.MeshStandardMaterial({
          map: texture,
          transparent: true,
          opacity: 0.4,
          side: THREE.DoubleSide,
          depthWrite: false,
        })
      )
      earthRef.current?.add(cloudMesh)
    })
    
    return () => {}
  }, [])
  
  useFrame(({ clock }) => {
    if (earthRef.current) {
      earthRef.current.rotation.y = clock.getElapsedTime() * 0.02
    }
    if (atmosphereRef.current) {
      atmosphereRef.current.rotation.y = clock.getElapsedTime() * 0.01
    }
  })
  
  return (
    <>
      <mesh ref={earthRef} receiveShadow>
        <sphereGeometry args={[EARTH_RADIUS, 64, 64]} />
        <meshStandardMaterial
          color={0x1a2a4a}
          roughness={0.8}
          metalness={0.1}
        />
      </mesh>
      
      <mesh ref={atmosphereRef} renderOrder={1}>
        <sphereGeometry args={[EARTH_RADIUS + 8, 64, 64]} />
        <meshBasicMaterial
          color={0x0088ff}
          transparent
          opacity={0.08}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>
      
      <ParticleField />
    </>
  )
}

export function GlobeScene() {
  const { threats, packets, showArcs, showThreatsOnly } = useStore()
  
  const threatArcs = useMemo(() => {
    if (!showArcs || showThreatsOnly) return []
    
    return threats
      .filter(t => t.threat_score > 0.3 && t.src_lat && t.dst_lat)
      .slice(0, 50)
      .map((threat, i) => ({
        ...threat,
        color: new THREE.Color(
          threat.threat_score > 0.7 ? 0xFF0033 :
          threat.threat_score > 0.5 ? 0xFF8800 :
          threat.threat_score > 0.3 ? 0xFFCC00 :
          0x39FF14
        ),
        progress: 0,
        intensity: 1 + threat.threat_score,
      }))
  }, [threats, showArcs, showThreatsOnly])
  
  return (
    <>
      <Earth />
      
      {threatArcs.map((arc, i) => (
        <ThreatArc
          key={`${arc.src_ip}-${arc.dst_ip}-${i}`}
          startLat={arc.src_lat}
          startLon={arc.src_lon}
          endLat={arc.dst_lat}
          endLon={arc.dst_lon}
          color={arc.color}
          progress={0.5}
          intensity={arc.intensity}
        />
      ))}
    </>
  )
}