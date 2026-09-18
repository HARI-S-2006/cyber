import { useFrame, useThree } from '@react-three/fiber'
import { useMemo, useRef, useEffect } from 'react'
import * as THREE from 'three'
import { OrbitControls, Stars } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
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
  const lineRef = useRef<THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial> | null>(null)
  
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
    opacity: 0.8,
    linewidth: 3,
  }), [color])
  
  // Initialize the line
  useEffect(() => {
    if (!lineRef.current) {
      lineRef.current = new THREE.Line(geometry, material)
    }
  }, [])
  
  // Animate the line progress
  useFrame(({ clock }) => {
    if (!lineRef.current) return
    
    // Create a laser pulse effect traveling along the arc
    const p = Math.min(1, (clock.getElapsedTime() * 0.5) % 1)
    const positions = geometry.attributes.position.array as Float32Array
    
    // We update the draw range to simulate a beam shooting across
    const drawPoints = Math.floor(p * 32)
    geometry.setDrawRange(0, drawPoints)
    
    geometry.attributes.position.needsUpdate = true
  })
  
  return lineRef.current ? <primitive object={lineRef.current} /> : null
}

function CyberEarth({ isUnderAttack }: { isUnderAttack: boolean }) {
  const earthRef = useRef<THREE.Mesh>(null)
  const wireframeRef = useRef<THREE.Mesh>(null)
  
  const targetColor = useMemo(() => new THREE.Color(isUnderAttack ? 0xFF0033 : 0x00FF41), [isUnderAttack])
  const coreTargetColor = useMemo(() => new THREE.Color(isUnderAttack ? 0x220005 : 0x020813), [isUnderAttack])
  
  useFrame(({ clock }) => {
    if (earthRef.current) {
      earthRef.current.rotation.y = clock.getElapsedTime() * 0.05
      const material = earthRef.current.material as THREE.MeshBasicMaterial
      material.color.lerp(coreTargetColor, 0.05)
    }
    if (wireframeRef.current) {
      wireframeRef.current.rotation.y = clock.getElapsedTime() * 0.05
      const material = wireframeRef.current.material as THREE.MeshBasicMaterial
      material.color.lerp(targetColor, 0.05)
    }
  })
  
  return (
    <group>
      {/* Solid inner core */}
      <mesh ref={earthRef as any}>
        <icosahedronGeometry args={[EARTH_RADIUS * 0.98, 4]} />
        <meshBasicMaterial
          color={0x020813}
          transparent
          opacity={0.9}
        />
      </mesh>
      
      {/* Glowing wireframe outer layer */}
      <mesh ref={wireframeRef as any}>
        <icosahedronGeometry args={[EARTH_RADIUS, 4]} />
        <meshBasicMaterial
          color={0x00FF41}
          wireframe
          transparent
          opacity={0.3}
        />
      </mesh>
    </group>
  )
}

function DataNodes() {
  const nodesRef = useRef<THREE.Points>(null)
  const count = 1000
  
  useEffect(() => {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const radius = EARTH_RADIUS + Math.random() * 20
      const phi = Math.acos(2 * Math.random() - 1)
      const theta = 2 * Math.PI * Math.random()
      
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.cos(phi)
      positions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta)
    }
    
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    
    const material = new THREE.PointsMaterial({
      color: 0x00FFFF,
      size: 0.5,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    })
    
    if (nodesRef.current) {
      nodesRef.current.geometry = geometry
      nodesRef.current.material = material
    }
  }, [])
  
  useFrame(({ clock }) => {
    if (nodesRef.current) {
      nodesRef.current.rotation.y = clock.getElapsedTime() * 0.03
      nodesRef.current.rotation.z = Math.sin(clock.getElapsedTime() * 0.01) * 0.1
    }
  })
  
  return <points ref={nodesRef as any} />
}

export function GlobeScene() {
  const { threats, showArcs, showThreatsOnly } = useStore()
  
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
  
  const isUnderAttack = useMemo(() => {
    if (threats.length === 0) return false;
    const latestTimestamp = threats[0].timestamp;
    return (Date.now() / 1000 - latestTimestamp) < 15;
  }, [threats])

  return (
    <>
      <OrbitControls 
        enablePan={false} 
        enableZoom={true} 
        minDistance={60} 
        maxDistance={300}
        autoRotate={true}
        autoRotateSpeed={0.5}
      />
      
      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
      
      <CyberEarth isUnderAttack={isUnderAttack} />
      <DataNodes />
      
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

      <EffectComposer>
        <Bloom 
          luminanceThreshold={0.2} 
          luminanceSmoothing={0.9} 
          intensity={1.5} 
          mipmapBlur 
        />
      </EffectComposer>
    </>
  )
}