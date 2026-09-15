import React, { useRef, useEffect, useMemo, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { OrbitControls } from '@react-three/drei'
import { useStore } from '../hooks/useStore'

const EARTH_RADIUS = 100
const ARC_HEIGHT_SCALE = 30
const MAX_ARCS = 500

function ipToLatLon(ip) {
  const parts = ip.split('.').map(Number)
  if (parts.length !== 4) return { lat: 0, lon: 0 }
  
  const hash = ((parts[0] * 256 + parts[1]) * 256 + parts[2]) * 256 + parts[3]
  const lat = (hash % 180) - 90
  const lon = ((hash >> 8) % 360) - 180
  return { lat, lon }
}

function latLonToVector3(lat, lon, radius = EARTH_RADIUS) {
  const phi = (90 - lat) * Math.PI / 180
  const theta = (lon + 180) * Math.PI / 180
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  )
}

function createArcGeometry(start, end, height) {
  const curve = new THREE.QuadraticBezierCurve3(
    start,
    new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5).normalize().multiplyScalar(EARTH_RADIUS + height),
    end
  )
  return new THREE.TubeGeometry(curve, 16, 0.3, 8, false)
}

const GlobeArcs = React.memo(({ arcs, timeWindow, colorScale }) => {
  const groupRef = useRef(new THREE.Group())
  const arcMeshesRef = useRef(new Map())
  
  useFrame(() => {
    const now = Date.now()
    const cutoff = now - timeWindow
    
    arcs.forEach(arc => {
      if (arc.timestamp < cutoff) return
      
      let mesh = arcMeshesRef.current.get(`${arc.src}-${arc.dst}`)
      if (!mesh) {
        const start = latLonToVector3(...Object.values(ipToLatLon(arc.src)))
        const end = latLonToVector3(...Object.values(ipToLatLon(arc.dst)))
        const height = ARC_HEIGHT_SCALE * (1 + arc.score * 5)
        
        const geometry = createArcGeometry(start, end, height)
        const material = new THREE.MeshBasicMaterial({
          color: colorScale(arc.score),
          transparent: true,
          opacity: 0.6,
          side: THREE.DoubleSide
        })
        mesh = new THREE.Mesh(geometry, material)
        mesh.userData = { arc, createdAt: now }
        groupRef.current.add(mesh)
        arcMeshesRef.current.set(`${arc.src}-${arc.dst}`, mesh)
      }
      
      const age = now - mesh.userData.createdAt
      const fadeIn = Math.min(age / 500, 1)
      const fadeOut = Math.max(0, 1 - (age - timeWindow + 5000) / 5000)
      mesh.material.opacity = 0.6 * fadeIn * fadeOut
      mesh.material.color.set(colorScale(arc.score))
      mesh.userData.arc = arc
    })
    
    arcMeshesRef.current.forEach((mesh, key) => {
      if (now - mesh.userData.createdAt > timeWindow + 10000) {
        groupRef.current.remove(mesh)
        mesh.geometry.dispose()
        mesh.material.dispose()
        arcMeshesRef.current.delete(key)
      }
    })
  })
  
  return <primitive object={groupRef.current} />
})

const GlobeSurface = () => {
  const meshRef = useRef()
  const { showHeatmap } = useStore()
  
  useEffect(() => {
    if (!meshRef.current) return
    
    const loader = new THREE.TextureLoader()
    loader.load('/earth-day.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      meshRef.current.material.map = texture
      meshRef.current.material.needsUpdate = true
    })
    
    loader.load('/earth-night.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      meshRef.current.material.emissiveMap = texture
      meshRef.current.material.emissive = new THREE.Color(0x332211)
      meshRef.current.material.emissiveIntensity = 0.5
      meshRef.current.material.needsUpdate = true
    })
    
    loader.load('/earth-specular.jpg', (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      meshRef.current.material.specularMap = texture
      meshRef.current.material.specular = new THREE.Color(0x111133)
      meshRef.current.material.needsUpdate = true
    })
    
    loader.load('/earth-clouds.jpg', (texture) => {
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
          depthWrite: false
        })
      )
      meshRef.current.parent.add(cloudMesh)
      meshRef.current.userData.cloudMesh = cloudMesh
    })
    
    return () => {
      if (meshRef.current.userData.cloudMesh) {
        meshRef.current.parent.remove(meshRef.current.userData.cloudMesh)
      }
    }
  }, [])
  
  useFrame(({ clock }) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = clock.getElapsedTime() * 0.02
      if (meshRef.current.userData.cloudMesh) {
        meshRef.current.userData.cloudMesh.rotation.y = clock.getElapsedTime() * 0.03
      }
    }
  })
  
  return (
    <mesh ref={meshRef} receiveShadow>
      <sphereGeometry args={[EARTH_RADIUS, 64, 64]} />
      <meshStandardMaterial
        color={0x1a2a4a}
        roughness={0.8}
        metalness={0.1}
      />
    </mesh>
  )
}

const Atmosphere = () => {
  const meshRef = useRef()
  
  useFrame(({ clock }) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = clock.getElapsedTime() * 0.01
    }
  })
  
  return (
    <mesh ref={meshRef} renderOrder={1}>
      <sphereGeometry args={[EARTH_RADIUS + 8, 64, 64]} />
      <meshBasicMaterial
        color={0x0088ff}
        transparent
        opacity={0.08}
        side={THREE.BackSide}
        depthWrite={false}
      />
    </mesh>
  )
}

const ParticleSystem = ({ count = 2000 }) => {
  const pointsRef = useRef()
  const { showParticles, anomalies } = useStore()
  
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    const positions = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    const colors = new Float32Array(count * 3)
    const alphas = new Float32Array(count)
    
    for (let i = 0; i < count; i++) {
      const radius = EARTH_RADIUS + Math.random() * 50
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
    
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.setAttribute('alpha', new THREE.BufferAttribute(alphas, 1))
    return geo
  }, [count])
  
  const material = useMemo(() => new THREE.PointsMaterial({
    size: 1.5,
    vertexColors: true,
    transparent: true,
    opacity: 0.6,
    sizeAttenuation: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  }), [])
  
  useFrame(({ clock }) => {
    if (!pointsRef.current || !showParticles) return
    
    const positions = pointsRef.current.geometry.attributes.position.array
    const alphas = pointsRef.current.geometry.attributes.alpha.array
    const time = clock.getElapsedTime()
    
    for (let i = 0; i < count; i++) {
      const idx = i * 3
      positions[idx + 1] += Math.sin(time + i) * 0.02
      alphas[i] = 0.1 + Math.sin(time * 2 + i) * 0.05
    }
    
    pointsRef.current.geometry.attributes.position.needsUpdate = true
    pointsRef.current.geometry.attributes.alpha.needsUpdate = true
    pointsRef.current.material.opacity = showParticles ? 0.6 : 0
  })
  
  return <points ref={pointsRef} geometry={geometry} material={material} />
}

const ColorScale = ({ value }) => {
  if (value > 0.8) return new THREE.Color(0xff0000)
  if (value > 0.6) return new THREE.Color(0xff8800)
  if (value > 0.4) return new THREE.Color(0xffdd00)
  if (value > 0.2) return new THREE.Color(0x00ff88)
  return new THREE.Color(0x0088ff)
}

const colorScale = (value) => {
  if (value > 0.8) return 0xff0000
  if (value > 0.6) return 0xff8800
  if (value > 0.4) return 0xffdd00
  if (value > 0.2) return 0x00ff88
  return 0x0088ff
}

export function GlobeScene() {
  const { globeRotation, globeZoom, showHeatmap, showParticles, globeData, arcTimeWindow } = useStore()
  const { camera } = useThree()
  
  useFrame(() => {
    camera.position.z = 300 * globeZoom
    camera.lookAt(0, 0, 0)
  })
  
  return (
    <Canvas
      camera={{ position: [0, 0, 300], fov: 40 }}
      style={{ width: '100%', height: '100%' }}
      gl={{ antialias: true, alpha: true, preserveDrawingBuffer: false }}
      shadows
    >
      <color attach="background" args={['#0a0e17']} />
      <fog attach="fog" args={['#0a0e17', 200, 800]} />
      
      <ambientLight intensity={0.4} color="#ffffff" />
      <directionalLight position={[200, 200, 200]} intensity={1.2} color="#ffffff" castShadow />
      <directionalLight position={[-200, -100, -200]} intensity={0.3} color="#0088ff" />
      <pointLight position={[0, 0, 0]} color="#0088ff" intensity={0.5} distance={500} decay={2} />
      
      <GlobeSurface />
      <Atmosphere />
      <ParticleSystem />
      
      {globeData && (
        <GlobeArcs
          arcs={globeData.arcs}
          timeWindow={arcTimeWindow}
          colorScale={colorScale}
        />
      )}
      
      <OrbitControls
        enablePan={false}
        enableZoom={true}
        minZoom={0.5}
        maxZoom={3}
        autoRotate={true}
        autoRotateSpeed={0.3}
        target={[0, 0, 0]}
      />
    </Canvas>
  )
}

export default GlobeScene