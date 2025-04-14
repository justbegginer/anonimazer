package com.example.anonimazer.controllers;

import com.example.anonimazer.models.Photo;
import com.example.anonimazer.models.User;
import com.example.anonimazer.repo.PhotoRepository;
import com.example.anonimazer.services.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.Principal;
import java.util.List;

@Controller
@RequestMapping("/anonimazer/photo")
public class PhotoController {

    private static final String UPLOAD_DIR = "uploads";

    @Autowired
    private UserService userService;

    @Autowired
    private PhotoRepository photoRepository;

    @GetMapping
    public String uploadPhoto(){
        return "uploadPhoto";
    }

    @PostMapping("/upload")
    public String handleFileUpload(@RequestParam("files") MultipartFile[] files,
                                   RedirectAttributes redirectAttributes) throws IOException {

        if (files.length == 0) {
            return "redirect:/anonimazer/photo/result";
        }

        Path uploadPath = Paths.get(UPLOAD_DIR);
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String username = auth.getName();
        User user = userService.findByLogin(username).orElseThrow();

        for (MultipartFile file : files) {
            if (!file.isEmpty()) {
                String filename = System.currentTimeMillis() + "_" + file.getOriginalFilename();
                Path destination = uploadPath.resolve(filename);
                Files.copy(file.getInputStream(), destination, StandardCopyOption.REPLACE_EXISTING);

                Photo photo = new Photo();
                photo.setFilename(filename);
                photo.setOwner(user);
                photoRepository.save(photo);
            }
        }

        return "redirect:/anonimazer/photo/result";
    }

    @GetMapping("/result")
    public String showResult(@RequestParam(value = "filename", required = false) String filename,
                             Model model, Principal principal) {

        User user = userService.findByLogin(principal.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));

        List<Photo> photos = photoRepository.findByOwner(user);

        List<String> filenames = photos.stream()
                .map(Photo::getFilename)
                .toList();

        model.addAttribute("filenames", filenames);
        return "result";
    }

    @PostMapping("/delete")
    public String deletePhoto(@RequestParam("filename") String filename, Principal principal, RedirectAttributes redirectAttributes) {
        Photo photo = photoRepository.findByFilename(filename)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));

        // Проверка владельца
        if (!photo.getOwner().getLogin().equals(principal.getName())) {
            return "forbidden";
        }

        // Удаление файла
        try {
            Path path = Paths.get("uploads").resolve(filename);
            Files.deleteIfExists(path);
        } catch (IOException e) {
            e.printStackTrace(); // можно логировать
        }

        // Удаление из базы данных
        photoRepository.delete(photo);

        // Редирект на result без filename, чтобы показать все оставшиеся
        return "redirect:/anonimazer/photo/result";
    }
}
