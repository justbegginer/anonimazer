package com.example.anonimazer.repo;

import com.example.anonimazer.models.Photo;
import com.example.anonimazer.models.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PhotoRepository extends JpaRepository<Photo, Long> {
    Optional<Photo> findByFilename(String filename);

    List<Photo> findByOwner(User user);
}

